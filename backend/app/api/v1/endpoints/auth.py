# -*- coding: utf-8 -*-
"""
认证端点
"""
import re
import time
import logging
from datetime import timedelta
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    oauth2_scheme,
)
from app.core.token_blacklist import add_token_to_blacklist
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 登录尝试记录: {username: [timestamp1, timestamp2, ...]}
_login_attempts: Dict[str, list] = {}
# 锁定账户记录: {username: unlock_timestamp}
_locked_accounts: Dict[str, float] = {}


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    
    要求:
    - 最小长度 8 字符
    - 必须包含大小写字母、数字、特殊字符中的至少2种
    
    返回: (是否通过, 错误消息)
    """
    if len(password) < 8:
        return False, "密码长度至少为 8 个字符"
    
    # 检查字符类型
    has_lowercase = bool(re.search(r'[a-z]', password))
    has_uppercase = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))
    
    # 统计包含的种类数
    types_count = sum([has_lowercase, has_uppercase, has_digit, has_special])
    
    if types_count < 2:
        # 构建错误提示
        missing_types = []
        if not has_lowercase:
            missing_types.append("小写字母")
        if not has_uppercase:
            missing_types.append("大写字母")
        if not has_digit:
            missing_types.append("数字")
        if not has_special:
            missing_types.append("特殊字符(!@#$%^&*等)")
        
        return False, f"密码必须包含至少2种字符类型，当前缺少: {', '.join(missing_types)}"
    
    return True, ""


def _cleanup_old_attempts(username: str, max_age_seconds: int = 900):
    """清理旧的登录尝试记录"""
    current_time = time.time()
    if username in _login_attempts:
        _login_attempts[username] = [
            ts for ts in _login_attempts[username]
            if current_time - ts < max_age_seconds
        ]
        if not _login_attempts[username]:
            del _login_attempts[username]


def _check_login_attempts(username: str) -> bool:
    """检查是否超过登录尝试限制"""
    current_time = time.time()
    _cleanup_old_attempts(username)
    
    # 检查是否被锁定
    if username in _locked_accounts:
        if current_time < _locked_accounts[username]:
            remaining = int(_locked_accounts[username] - current_time)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录尝试过多，请 {remaining} 秒后重试"
            )
        else:
            # 解除锁定
            del _locked_accounts[username]
            if username in _login_attempts:
                del _login_attempts[username]
    
    # 检查尝试次数
    if username in _login_attempts:
        attempts = len(_login_attempts[username])
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            # 锁定账户
            _locked_accounts[username] = current_time + (settings.LOGIN_LOCKOUT_MINUTES * 60)
            logger.warning(f"账户 {username} 因登录尝试过多已被锁定 {settings.LOGIN_LOCKOUT_MINUTES} 分钟")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录尝试过多，账户已被锁定 {settings.LOGIN_LOCKOUT_MINUTES} 分钟"
            )
    
    return True


def _record_login_attempt(username: str):
    """记录登录尝试"""
    current_time = time.time()
    if username not in _login_attempts:
        _login_attempts[username] = []
    _login_attempts[username].append(current_time)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    # 验证密码强度
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # 检查用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if user_data.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
    
    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    username = form_data.username
    
    # 检查登录尝试限制
    _check_login_attempts(username)
    
    # 查找用户
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        # 记录失败的登录尝试
        _record_login_attempt(username)
        logger.warning(f"登录失败: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    
    # 登录成功，清除尝试记录
    if username in _login_attempts:
        del _login_attempts[username]
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    logger.info(f"用户登录成功: {username}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """用户登出 - 使 token 失效"""
    # 将 token 加入黑名单
    await add_token_to_blacklist(token)
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前用户信息"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户信息"""
    if user_data.email is not None:
        current_user.email = user_data.email
    if user_data.steam_id is not None:
        current_user.steam_id = user_data.steam_id
    if user_data.buff_cookie is not None:
        current_user.buff_cookie = user_data.buff_cookie
    if user_data.ma_file is not None:
        current_user.ma_file = user_data.ma_file
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

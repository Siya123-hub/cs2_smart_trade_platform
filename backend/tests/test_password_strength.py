# -*- coding: utf-8 -*-
"""
密码强度验证测试
"""
import pytest
from app.api.v1.endpoints.auth import validate_password_strength


class TestPasswordStrength:
    """密码强度验证测试"""
    
    def test_password_too_short(self):
        """测试密码太短"""
        is_valid, error = validate_password_strength("abc")
        assert is_valid is False
        assert "8" in error
    
    def test_password_exactly_8_chars(self):
        """测试正好8字符但缺少其他类型"""
        is_valid, error = validate_password_strength("abcdefgh"
        )
        assert is_valid is False
        assert "数字" in error or "特殊字符" in error
    
    def test_password_with_lowercase_and_digit(self):
        """测试包含小写字母和数字"""
        is_valid, error = validate_password_strength("abcdef12"
        )
        assert is_valid is True
        assert error == ""
    
    def test_password_with_uppercase_and_digit(self):
        """测试包含大写字母和数字"""
        is_valid, error = validate_password_strength("ABCDEF12"
        )
        assert is_valid is True
        assert error == ""
    
    def test_password_with_digit_and_special(self):
        """测试包含数字和特殊字符"""
        is_valid, error = validate_password_strength("abcd123!"
        )
        assert is_valid is True
        assert error == ""
    
    def test_password_with_all_types(self):
        """测试包含所有类型字符"""
        is_valid, error = validate_password_strength("Abcd123!"
        )
        assert is_valid is True
        assert error == ""
    
    def test_password_only_lowercase(self):
        """测试仅小写字母"""
        is_valid, error = validate_password_strength("abcdefgh"
        )
        assert is_valid is False
    
    def test_password_only_numbers(self):
        """测试仅数字"""
        is_valid, error = validate_password_strength("12345678"
        )
        assert is_valid is False
    
    def test_password_with_space(self):
        """测试密码包含空格"""
        is_valid, error = validate_password_strength("Abc 123!"
        )
        assert is_valid is True  # 空格算特殊字符

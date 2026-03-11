# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0.0] - 2026-03-11

### Added
- **统一响应格式**: 新增 `ServiceResponse` 类，统一所有服务的返回格式
- **审计日志加密**: 审计日志支持加密存储，从 `ENCRYPTION_KEY` 读取密钥

### Changed
- **Buff API 重试机制**: 线性退避 → 指数退避 + 随机抖动 (5s→10s→20s，最大60s)
- **Steam Session 健康检查**: 新增 `health_check()` 和 `ensure_healthy_session()` 方法
- **幂等性 Key 算法**: JSON 请求体排序后再生成 hash，支持乱序 JSON

### Fixed
- **P1-1**: Buff API 429 错误重试效率问题 - 使用指数退避算法
- **P1-2**: 交易服务返回格式不一致 - 统一使用 ServiceResponse
- **P1-3**: Steam Session 健康检查缺失 - 添加健康检查和自动重建
- **P1-4**: 幂等性 Key JSON 顺序问题 - 递归排序字典键
- **P1-5**: 审计日志明文存储 - 添加 Fernet 加密支持

### Security
- 审计日志敏感信息加密存储

---

## [0.9.0] - 2026-03-10

### Added
- 分布式限流支持
- 登录失败锁定机制
- 监控服务支持
- 加密 Salt 轮换支持

### Fixed
- 第17轮安全问题和技术债务修复

---

## [0.8.0] - 2026-03-10

### Added
- 加密异常处理降级策略
- 数据库连接池优化

---

## [0.7.0] - 2026-03-09

### Added
- 基础交易功能
- BUFF/Steam 双平台价格监控
- Web 管理面板 (Vue 3)
- RESTful API

---

[Unreleased]: https://github.com/yourusername/cs2-trade-platform/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/cs2-trade-platform/releases/tag/v1.0.0
[0.9.0]: https://github.com/yourusername/cs2-trade-platform/compare/v0.9.0...v1.0.0
[0.8.0]: https://github.com/yourusername/cs2-trade-platform/compare/v0.8.0...v0.9.0
[0.7.0]: https://github.com/yourusername/cs2-trade-platform/compare/v0.7.0...v0.8.0

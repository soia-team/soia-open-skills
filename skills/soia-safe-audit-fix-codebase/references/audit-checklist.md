# 安全审计清单

## 使用方法

先识别技术栈、入口和信任边界，只使用相关条目。清单用于防遗漏，不是把每一项都写成 Finding。每条候选必须有可达性和反证检查。

## 1. 架构与信任边界

- 外部 HTTP/RPC/消息/文件/定时任务入口是否完整；
- 用户、服务、租户、管理员和第三方之间的信任边界；
- 敏感数据、凭据、密钥、上传文件和审计日志的流向；
- 服务端出网、回调、Webhook、代理和元数据访问；
- 生产与测试、控制面与数据面、同步与异步边界。

## 2. 身份、会话与授权

- 登录、注册、找回、MFA、Token 签发/刷新/撤销；
- 会话固定、Cookie 属性、CSRF、JWT 验签和算法约束；
- 对象级、功能级、字段级和租户级授权；
- 管理端、内部接口、调试端点和健康检查；
- 默认账号、弱权限边界、过度授权和 confused deputy。

## 3. 输入与注入

- SQL/NoSQL/LDAP/XPath/模板/表达式注入；
- shell/进程参数、命令拼接和环境变量继承；
- SSRF、URL 解析差异、重定向、DNS rebinding 和非 HTTP scheme；
- XSS、HTML/Markdown 渲染、响应头和开放重定向；
- GraphQL、搜索、过滤、排序和动态字段表达式。

## 4. 反序列化与类型解析

- Java/Python/PHP/.NET/Node 原生或第三方反序列化；
- JSON/XML/YAML 的类型元数据、AutoType、多态和自定义 resolver；
- Object/Map/Any/接口字段中的嵌套类型控制；
- 类加载、插件、脚本、模板和远程资源解析；
- 消息队列、缓存和数据库中的历史序列化数据。

## 5. 文件、路径与归档

- 路径穿越、绝对路径、符号链接和 TOCTOU；
- 上传扩展名、MIME、内容、大小、解压缩和杀毒边界；
- Zip Slip、压缩炸弹、临时文件权限和清理；
- 下载鉴权、Content-Disposition、公开桶和备份；
- 文件转换器、图片/PDF/Office 解析器及外部进程。

## 6. 密码学与秘密

- 密钥、Token、密码、Cookie、连接串是否进入代码、日志或制品；
- 随机数、哈希、签名、加密模式、nonce/IV 和密钥轮换；
- TLS 验证、证书信任、hostname check 和明文降级；
- 口令存储、密码重置 Token 和时间比较；
- KMS/Secret Manager 权限与失败降级。

## 7. 数据与业务逻辑

- 批量赋值、越权字段、状态机跳转和重复提交；
- 金额、配额、库存、幂等、竞态和并发一致性；
- 分页/导出绕过、批量接口、搜索侧信道；
- 删除、恢复、审计、留存和跨租户缓存；
- 错误路径是否 fail-open、吞错或回退到不安全默认值。

## 8. 依赖与供应链

- 直接/传递依赖、锁文件、最终制品和镜像是否一致；
- 依赖版本、可达调用、配置与部署前提；
- 包名混淆、未锁定来源、脚本钩子和不可信构建下载；
- CI action/plugin 镜像是否固定到可控版本或摘要；
- 构建日志、制品签名、SBOM 和发布权限。

## 9. 运行时、容器与 IaC

- 是否 root、Linux capabilities、seccomp/AppArmor、只读文件系统；
- 网络入口/出口、服务账户、云 IAM 和元数据保护；
- Kubernetes RBAC、Secret、hostPath、hostNetwork 和特权容器；
- Terraform/CloudFormation 权限、公开存储、Security Group；
- 调试模式、管理端口、JMX/Actuator、错误页和指标暴露。

## 10. 日志、隐私与响应

- 日志是否包含凭据、个人数据、支付/健康数据或请求体；
- 安全事件是否有稳定 ID、主体、目标、结果和时间；
- 告警是否能发现异常登录、权限变更、出网和子进程；
- 错误响应是否泄露堆栈、路径、SQL 或内部主机；
- 轮换、隔离、取证和回滚路径是否真实可用。

## 技术栈路由

| 线索 | 继续检查 |
|---|---|
| `pom.xml` / `build.gradle` / Spring | 反序列化、Actuator、SpEL、MVC converter、JDBC/JPA、fat-jar 依赖 |
| `package.json` | 原型污染、模板/XSS、child_process、SSRF、lockfile 和 install scripts |
| `requirements.txt` / `pyproject.toml` | pickle/YAML、模板、subprocess、路径、debug server、依赖 hash |
| `go.mod` | HTTP client/redirect、模板、命令、路径、JWT、goroutine/竞态 |
| `Cargo.toml` | unsafe、命令、路径、serde 自定义、FFI、panic/error 边界 |
| Docker/Kubernetes/Terraform | 身份权限、秘密、网络、特权、镜像和供应链 |

## 证据门

报告 Finding 前至少回答：

1. 输入由谁控制？
2. 危险调用是否真实可达？
3. 中间是否已有验证、编码、权限或框架防护？
4. 运行/部署条件是否满足？
5. 能否用无害 fixture、测试或官方资料独立复核？
6. 误报时最可能错在哪一步？

任一关键答案未知时标记 `needs-evidence`，不要伪装成 confirmed。

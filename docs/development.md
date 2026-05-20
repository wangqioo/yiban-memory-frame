# 本地开发

当前 MVP 不依赖第三方包，适合先在 Windows 或 RK3576 Linux 上快速运行。

## 启动

在仓库根目录执行：

```bash
python services/api-server/server.py
```

访问：

- 老人端：http://localhost:8080/device/
- 家属端：http://localhost:8080/family/
- API 状态：http://localhost:8080/api/state

## 演示流程

1. 打开老人端，查看相册轮播。
2. 打开家属端，发送一条留言。
3. 在老人端点击“坐到相册前”，进入面对面陪伴模式。
4. 在老人端输入框模拟老人语音，例如：“小宝又长高了，像他妈妈小时候。”
5. 家属端点击“生成今日摘要”。
6. 查看亲情摘要和最近对话。

## 数据

运行后默认会生成：

```text
~/.yiban-memory-frame/data/state.json
```

这是 MVP 的本地 JSON 数据库。可以通过 `YIBAN_DATA_DIR` 环境变量改写数据目录。后续会替换为 PostgreSQL + 对象存储。

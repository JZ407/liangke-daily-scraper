# 量科网每日新闻自动抓取工作流

## 文件说明

| 文件 | 作用 |
|------|------|
| `extract_cookie.py` | 从 Edge 浏览器提取登录 Cookie |
| `scrape_daily.py` | 每日新闻抓取脚本 |
| `update_cookie.bat` | 一键更新 Cookie（登录后运行） |
| `run_daily.bat` | 一键运行每日抓取 |

## 使用流程

### 第一次使用（或 Cookie 过期后）

1. **在 Edge 浏览器中登录量科网**
   - 打开 Edge，访问 http://www.qtc.com.cn
   - 点击右上角登录按钮，输入账号密码
   - 确保登录成功（能看到欢迎信息）

2. **更新 Cookie**
   - 双击运行 `update_cookie.bat`
   - 脚本会自动启动 Edge（带调试端口），提取 Cookie，保存到桌面
   - 看到 "Cookie updated successfully" 即完成

### 每日自动抓取

**手动运行：**
- 双击运行 `run_daily.bat`
- 脚本会自动提取最新 Cookie，然后抓取当天新闻
- 结果保存到：`桌面\量科网每日新闻\YYYY-MM-DD_量科网新闻.txt`

**设置 Windows 定时任务（推荐）：**
1. 按 `Win + R`，输入 `taskschd.msc` 回车
2. 右侧点击 "创建基本任务"
3. 名称：量科网每日抓取
4. 触发器：每天，设置一个时间（如 每天上午 9:00）
5. 操作：启动程序
6. 程序路径：浏览到 `run_daily.bat`
7. 完成

**注意事项：**
- 如果 Cookie 过期（约 1 周），需要重新运行 `update_cookie.bat`
- 建议每周一早上先运行 `update_cookie.bat`，再运行抓取

## 输出格式

```
量科网每日新闻抓取 - 2026-05-19
共 N 篇文章
======================================================================

======================================================================
标题: xxx
时间: 实时快讯量科网2026-05-19 11:14
链接: http://www.qtc.com.cn/flash/xxx.html
参考链接:
  - 参考链接¹: https://thequantuminsider.com/...
----------------------------------------------------------------------
[正文内容]
```

## 依赖要求

- Python 3.10+（已安装 `requests`, `beautifulsoup4`, `websocket-client`）
- Microsoft Edge 浏览器
- Windows 10/11

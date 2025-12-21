# 模块 6：安全中心与历史记录管理 (Security Center)

## 简介
**模块 6** 提供了一个全屏的仪表盘页面，用于用户查看历史拦截记录、管理个人黑名单以及学习安全知识。

作为**数据的展示层和管理层**，与后台数据进行交互。

## 功能特性
1.  **历史记录 (History)**
    *   展示由后台拦截模块生成的安全分析报告。
    *   支持查看拦截时间、URL、威胁等级及处理状态。
    *   支持清空历史记录。
2.  **黑名单管理 (Blacklist)**
    *   允许用户手动添加需要拦截的域名或 URL。
    *   支持查看和删除已添加的黑名单条目。
    *   数据直接写入本地存储，供拦截模块实时读取生效。
3.  **安全知识库 (Knowledge Base)**
    *   提供静态的安全教育内容（防钓鱼指南、HTTPS 说明等）。
    *   响应式卡片布局。

## 架构说明
本模块采用 **Full-page Extension (全屏扩展页)** 模式。
*   **入口**：通过点击扩展图标弹出的轻量级 `popup.html` (模块 4) 中的按钮跳转进入。
*   **页面**：`pages/security_center.html`
*   **布局**：响应式全屏布局 (100vw/100vh)，左侧导航栏 + 右侧内容区。

## 目录结构
```text
security_center/
├── css/
│   └── style.css          # 全局样式（含深色模式、玻璃拟态风格）
├── js/
│   ├── popup.js           # 入口跳转逻辑
│   └── security_center.js # 核心逻辑（Tab切换、数据CRUD、UI渲染）
├── pages/
│   ├── popup.html         # 扩展图标点击后的轻量级入口
│   └── security_center.html # 安全中心主仪表盘
├── images/                # 图标资源
└── manifest.json          # 扩展清单配置
```

## 数据存储说明与交互协议
所有持久化数据均存储于浏览器扩展的本地存储 **`chrome.storage.local`** 中，不依赖外部数据库。数据以 **JSON 格式** 序列化保存。

以下是各数据项的详细定义：

### 1. 历史记录 (`securityHistory`)
*   **读写权限**：模块 1/2 (写)，模块 6 (读/清空)。
*   **数据结构**：
    ```json
    [
      {
        "time": "2023-10-27 10:23",
        "url": "http://example.com",
        "threat": "High", // High, Medium, Low
        "status": "已拦截"
      }
    ]
    ```

### 2. 黑名单 (`userBlacklist`)
*   **读写权限**：模块 6 (读/写)，模块 1 (读)。
*   **数据结构**：纯字符串数组
    ```json
    ["evil-site.com", "phishing-example.net"]
    ```

## 协作指南
1.  **安装依赖**：本项目基于原生 HTML/CSS/JS，无需预编译步骤。
2.  **调试运行**：
    *   打开 Chrome/Edge 浏览器进入扩展管理页。
    *   开启“开发者模式”。
    *   点击“加载已解压的扩展程序”，选择 `security_center` 文件夹。
3.  **模拟数据**：
    *   如果本地没有真实拦截数据，`security_center.js` 会加载内置的 `mockHistory` 用于前端展示开发。
    *   可以通过控制台手动修改 storage 来测试：
        ```javascript
        chrome.storage.local.set({ userBlacklist: ['test.com'] })
        ```

## 待办事项 (TODO)
- [ ] 对接模块 2 的真实评分数据接口（如数据格式发生变更）。
- [ ] 增加搜索和分页功能（当历史记录过多时）。


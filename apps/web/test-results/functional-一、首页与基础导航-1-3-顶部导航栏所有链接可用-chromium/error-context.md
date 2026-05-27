# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: functional.spec.ts >> 一、首页与基础导航 >> 1.3 顶部导航栏所有链接可用
- Location: e2e\functional.spec.ts:73:7

# Error details

```
Test timeout of 30000ms exceeded.
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - main [ref=e2]:
    - generic [ref=e3]:
      - generic [ref=e5]:
        - generic [ref=e6]:
          - link "J Jarvis PM" [ref=e7] [cursor=pointer]:
            - /url: /
            - generic [ref=e8]: J
            - generic [ref=e9]: Jarvis PM
          - navigation [ref=e10]:
            - link "工作台" [ref=e11] [cursor=pointer]:
              - /url: /dashboard
            - link "写PRD" [ref=e12] [cursor=pointer]:
              - /url: /workspace
            - link "交付中心" [ref=e13] [cursor=pointer]:
              - /url: /delivery
            - link "模板管理" [ref=e14] [cursor=pointer]:
              - /url: /templates
            - link "需求Battle" [ref=e15] [cursor=pointer]:
              - /url: /battle
            - link "工作流" [ref=e16] [cursor=pointer]:
              - /url: /workflow
            - link "技能广场" [ref=e17] [cursor=pointer]:
              - /url: /skills
            - link "提示词" [ref=e18] [cursor=pointer]:
              - /url: /prompts
        - button "+ 新建 PRD" [ref=e20]
      - main [ref=e21]:
        - generic [ref=e22]:
          - generic [ref=e23]:
            - generic [ref=e24]:
              - heading "工具箱" [level=2] [ref=e25]
              - generic [ref=e26]:
                - button "🎯 用户研究" [ref=e27]:
                  - generic [ref=e28]: 🎯
                  - generic [ref=e29]: 用户研究
                - button "👥 干系人分析" [ref=e30]:
                  - generic [ref=e31]: 👥
                  - generic [ref=e32]: 干系人分析
                - button "⚔️ 竞品分析" [ref=e33]:
                  - generic [ref=e34]: ⚔️
                  - generic [ref=e35]: 竞品分析
                - button "📊 数据分析" [ref=e36]:
                  - generic [ref=e37]: 📊
                  - generic [ref=e38]: 数据分析
                - button "📋 评审材料" [ref=e39]:
                  - generic [ref=e40]: 📋
                  - generic [ref=e41]: 评审材料
                - button "🎨 原型设计" [ref=e42]:
                  - generic [ref=e43]: 🎨
                  - generic [ref=e44]: 原型设计
                - button "🧠 语义检索" [ref=e45]:
                  - generic [ref=e46]: 🧠
                  - generic [ref=e47]: 语义检索
            - generic [ref=e48]:
              - heading "项目统计" [level=2] [ref=e49]
              - generic [ref=e50]:
                - generic [ref=e51]:
                  - generic [ref=e52]: PRD 数量
                  - generic [ref=e53]: "0"
                - generic [ref=e54]:
                  - generic [ref=e55]: 行业
                  - generic [ref=e56]: 其他
                - generic [ref=e57]:
                  - generic [ref=e58]: 状态
                  - generic [ref=e59]: active
          - generic [ref=e60]:
            - generic [ref=e61]:
              - button "📝 PRD 文档" [ref=e62]:
                - generic [ref=e63]: 📝
                - generic [ref=e64]: PRD 文档
              - button "👤 用户画像" [ref=e65]:
                - generic [ref=e66]: 👤
                - generic [ref=e67]: 用户画像
              - button "⚔️ 竞品信息" [ref=e68]:
                - generic [ref=e69]: ⚔️
                - generic [ref=e70]: 竞品信息
              - button "📋 需求池" [ref=e71]:
                - generic [ref=e72]: 📋
                - generic [ref=e73]: 需求池
            - generic [ref=e74]:
              - heading "PRD 文档" [level=2] [ref=e75]
              - generic [ref=e76]:
                - generic [ref=e77]: 📝
                - generic [ref=e78]: 暂无 PRD 文档
                - generic [ref=e79]: 点击"+ 新建 PRD"创建第一份文档
  - button "🤖" [ref=e80]:
    - generic [ref=e81]: 🤖
  - region "Notifications alt+T"
  - alert [ref=e82]
```
import requests, json, os, time

BASE = 'http://127.0.0.1:8000/api/v1'
OUTPUT_DIR = 'test_outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(name, data):
    path = os.path.join(OUTPUT_DIR, f'{name}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'[SAVED] {path}')

def save_md(name, content):
    path = os.path.join(OUTPUT_DIR, f'{name}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[SAVED] {path}')

# 1. 创建项目
r = requests.post(f'{BASE}/projects', json={
    'name': '端到端验证项目',
    'description': '全面功能测试用项目',
    'industry': 'medical'
})
project = r.json()['data']
project_id = project['id']
save('01_create_project', r.json())

# 2. 项目列表
r = requests.get(f'{BASE}/projects')
save('02_list_projects', r.json())

# 3. 技能执行统计（Dashboard）
r = requests.get(f'{BASE}/skills/executions?limit=999')
save('03_skill_executions', r.json())

# 4. 工具箱 - 用户研究
print('[TEST] 用户研究...')
r = requests.post(f'{BASE}/tools/user-research', json={
    'project_id': project_id,
    'research_type': 'interview',
    'target_audience': '医护人员和患者'
}, timeout=120)
save('04_tool_user_research', r.json())

# 5. 工具箱 - 干系人分析
print('[TEST] 干系人分析...')
r = requests.post(f'{BASE}/tools/stakeholders', json={
    'project_id': project_id
}, timeout=120)
save('05_tool_stakeholders', r.json())

# 6. 工具箱 - 竞品分析
print('[TEST] 竞品分析...')
r = requests.post(f'{BASE}/tools/competitors', json={
    'project_id': project_id,
    'competitors': ['竞品A', '竞品B']
}, timeout=120)
save('06_tool_competitors', r.json())

# 7. 工具箱 - 数据分析
print('[TEST] 数据分析...')
r = requests.post(f'{BASE}/tools/data-analysis', json={
    'project_id': project_id,
    'data_source': '业务数据库',
    'metrics': ['日活跃用户', '转化率', '留存率']
}, timeout=120)
save('07_tool_data_analysis', r.json())

# 8. 工具箱 - 评审材料
print('[TEST] 评审材料...')
r = requests.post(f'{BASE}/tools/review-materials', json={
    'project_id': project_id,
    'material_type': 'agenda'
}, timeout=120)
save('08_tool_review_materials', r.json())

# 9. 工具箱 - 原型设计
print('[TEST] 原型设计...')
r = requests.post(f'{BASE}/tools/prototype', json={
    'project_id': project_id,
    'feature_description': '在线预约挂号功能原型',
    'prototype_type': 'wireframe'
}, timeout=120)
save('09_tool_prototype', r.json())

# 10. 创建 PRD（默认模板）
print('[TEST] 创建默认模板 PRD...')
r = requests.post(f'{BASE}/prds', json={
    'project_id': project_id,
    'title': '默认模板 PRD',
    'template': 'default'
}, timeout=120)
prd_default = r.json()['data']
save('10_prd_default', r.json())
save_md('10_prd_default_markdown', prd_default.get('markdown', ''))

# 11. 创建 PRD（医疗模板）
print('[TEST] 创建医疗模板 PRD...')
r = requests.post(f'{BASE}/prds', json={
    'project_id': project_id,
    'title': '医疗模板 PRD',
    'template': 'medical'
}, timeout=120)
prd_medical = r.json()['data']
save('11_prd_medical', r.json())
save_md('11_prd_medical_markdown', prd_medical.get('markdown', ''))

# 12. PRD 导出 Markdown
print('[TEST] PRD 导出 Markdown...')
export_url = f'{BASE}/prds/' + prd_medical['id'] + '/export?format=markdown'
r = requests.get(export_url)
save('12_prd_export_md', r.json())

# 13. PRD 章节生成
print('[TEST] PRD 章节生成...')
gen_url = f'{BASE}/prds/' + prd_medical['id'] + '/generate'
r = requests.post(gen_url, json={
    'chapter': '4',
    'prompt': '生成功能规格章节'
}, timeout=120)
save('13_prd_generate_chapter', r.json())

# 14. 工作流模板列表
r = requests.get(f'{BASE}/workflows/templates')
save('14_workflow_templates', r.json())

# 15. 工作流执行
print('[TEST] 执行工作流 product-design...')
r = requests.post(f'{BASE}/workflows/execute', json={
    'workflow_name': 'product-design',
    'inputs': {
        'idea': '医疗信息化产品',
        'targetUsers': '医护人员和患者',
        'industry': 'medical',
        'constraints': '必须符合等保三级和医疗数据隐私规范'
    },
    'project_id': project_id
}, timeout=300)
save('15_workflow_execute', r.json())

# 16. Battle 创建
print('[TEST] 创建 Battle...')
r = requests.post(f'{BASE}/battles', json={
    'name': '验证战役',
    'description': '全面功能验证用战役',
    'project_id': project_id,
    'days': [
        {'day': 'Day 1', 'task': '用户调研', 'status': 'pending', 'tool': 'research', 'notes': ''},
        {'day': 'Day 2', 'task': '竞品分析', 'status': 'pending', 'tool': 'research', 'notes': ''},
        {'day': 'Day 3', 'task': 'PRD框架搭建', 'status': 'pending', 'tool': 'prd', 'notes': ''},
        {'day': 'Day 4', 'task': '功能规格撰写', 'status': 'pending', 'tool': 'prd', 'notes': ''},
        {'day': 'Day 5', 'task': '评审材料准备', 'status': 'pending', 'tool': 'review', 'notes': ''}
    ]
})
battle = r.json()['data']
save('16_battle_create', r.json())

# 17. Battle 推进 Day 1（触发 AI 自动化）
print('[TEST] Battle 推进 Day 1（AI 自动化）...')
adv_url = f'{BASE}/battles/' + battle['id'] + '/advance'
r = requests.post(adv_url, timeout=120)
save('17_battle_advance_day1', r.json())

# 18. Battle 推进 Day 2
print('[TEST] Battle 推进 Day 2（AI 自动化）...')
r = requests.post(adv_url, timeout=120)
save('18_battle_advance_day2', r.json())

# 19. Battle 推进 Day 3（触发 PRD 自动生成）
print('[TEST] Battle 推进 Day 3（AI 自动生成 PRD）...')
r = requests.post(adv_url, timeout=120)
save('19_battle_advance_day3', r.json())

# 20. 查看最终项目下的 PRD 列表
r = requests.get(f'{BASE}/prds?project_id={project_id}')
save('20_final_prd_list', r.json())

print('\n[ALL TESTS COMPLETED]')

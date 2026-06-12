"use client";

import { useState } from "react";

// 医疗合规矩阵
interface ComplianceItem {
  id: string;
  category: string;
  item: string;
  regulation: string;
  required: boolean;
  checked: boolean;
  notes?: string;
}

const COMPLIANCE_CHECKLIST: ComplianceItem[] = [
  // 数据安全
  {
    id: "sec-1",
    category: "数据安全",
    item: "患者敏感信息加密存储",
    regulation: "《医疗机构病历管理规定》",
    required: true,
    checked: false,
    notes: "姓名、身份证号、手机号等需加密",
  },
  {
    id: "sec-2",
    category: "数据安全",
    item: "数据传输使用HTTPS/TLS加密",
    regulation: "等保三级要求",
    required: true,
    checked: false,
  },
  {
    id: "sec-3",
    category: "数据安全",
    item: "数据库访问权限控制",
    regulation: "等保三级要求",
    required: true,
    checked: false,
    notes: "最小权限原则，按需授权",
  },
  {
    id: "sec-4",
    category: "数据安全",
    item: "敏感数据展示脱敏",
    regulation: "《个人信息保护法》",
    required: true,
    checked: false,
    notes: "手机号显示138****1234格式",
  },

  // 隐私保护
  {
    id: "priv-1",
    category: "隐私保护",
    item: "患者授权机制",
    regulation: "《医疗机构管理条例》",
    required: true,
    checked: false,
    notes: "明确告知数据使用范围，获取同意",
  },
  {
    id: "priv-2",
    category: "隐私保护",
    item: "数据最小化原则",
    regulation: "《个人信息保护法》",
    required: true,
    checked: false,
    notes: "只收集业务必需的信息",
  },
  {
    id: "priv-3",
    category: "隐私保护",
    item: "数据保留期限设定",
    regulation: "《医疗机构病历管理规定》",
    required: true,
    checked: false,
    notes: "一般病历保存15年",
  },
  {
    id: "priv-4",
    category: "隐私保护",
    item: "患者数据导出/删除功能",
    regulation: "《个人信息保护法》",
    required: false,
    checked: false,
    notes: "支持患者申请数据副本或删除",
  },

  // 审计追溯
  {
    id: "audit-1",
    category: "审计追溯",
    item: "操作日志完整记录",
    regulation: "等保三级要求",
    required: true,
    checked: false,
    notes: "谁在什么时间做了什么操作",
  },
  {
    id: "audit-2",
    category: "审计追溯",
    item: "日志留存不少于6个月",
    regulation: "《网络安全法》",
    required: true,
    checked: false,
  },
  {
    id: "audit-3",
    category: "审计追溯",
    item: "异常操作告警机制",
    regulation: "等保三级要求",
    required: false,
    checked: false,
    notes: "如批量导出、非工作时间访问等",
  },

  // 业务合规
  {
    id: "biz-1",
    category: "业务合规",
    item: "借阅资质审核",
    regulation: "《医疗机构管理条例》第XX条",
    required: true,
    checked: false,
    notes: "确认申请人身份和用途合法性",
  },
  {
    id: "biz-2",
    category: "业务合规",
    item: "收费项目明码标价",
    regulation: "《价格法》",
    required: true,
    checked: false,
    notes: "公示收费标准，不得乱收费",
  },
  {
    id: "biz-3",
    category: "业务合规",
    item: "退款流程合规",
    regulation: "财务制度",
    required: true,
    checked: false,
    notes: "明确退款条件和时限",
  },

  // 系统安全
  {
    id: "sys-1",
    category: "系统安全",
    item: "身份认证机制",
    regulation: "等保三级要求",
    required: true,
    checked: false,
    notes: "强密码策略、定期更换",
  },
  {
    id: "sys-2",
    category: "系统安全",
    item: "登录失败锁定机制",
    regulation: "等保三级要求",
    required: true,
    checked: false,
    notes: "连续5次失败锁定15分钟",
  },
  {
    id: "sys-3",
    category: "系统安全",
    item: "会话超时机制",
    regulation: "等保三级要求",
    required: true,
    checked: false,
    notes: "无操作30分钟自动退出",
  },
];

// 多院区政策差异
interface MultiSitePolicy {
  site: string;
  policies: {
    item: string;
    value: string;
    note?: string;
  }[];
}

const MULTI_SITE_POLICIES: MultiSitePolicy[] = [
  {
    site: "江西院区",
    policies: [
      { item: "押金标准", value: "200元/片", note: "病理切片" },
      { item: "审核时效", value: "24小时", note: "工作日" },
      { item: "特殊要求", value: "需上传病理报告", note: "必须原件" },
    ],
  },
  {
    site: "临夏院区",
    policies: [
      { item: "押金标准", value: "150元/片", note: "病理切片" },
      { item: "审核时效", value: "48小时", note: "工作日" },
      { item: "特殊要求", value: "需当地医保备案", note: "外地患者" },
    ],
  },
  {
    site: "浙江院区",
    policies: [
      { item: "押金标准", value: "200元/片", note: "病理切片" },
      { item: "审核时效", value: "24小时", note: "工作日" },
      { item: "特殊要求", value: "支持医保支付", note: "需医保卡验证" },
    ],
  },
];

// 法规速查
interface Regulation {
  name: string;
  articles: {
    article: string;
    content: string;
    relevance: string;
  }[];
}

const REGULATIONS: Regulation[] = [
  {
    name: "《医疗机构管理条例》",
    articles: [
      {
        article: "第三十条",
        content: "医疗机构应当建立健全病历管理制度",
        relevance: "切片借阅需遵循病历管理规定",
      },
      {
        article: "第三十一条",
        content: "患者有权查阅、复制其病历资料",
        relevance: "患者申请借阅的法律依据",
      },
    ],
  },
  {
    name: "《个人信息保护法》",
    articles: [
      {
        article: "第十三条",
        content: "处理个人信息应当取得个人同意",
        relevance: "收集患者信息需获得授权",
      },
      {
        article: "第二十八条",
        content: "敏感个人信息需单独同意",
        relevance: "健康信息属于敏感信息",
      },
    ],
  },
  {
    name: "《网络安全等级保护条例》",
    articles: [
      {
        article: "等保三级要求",
        content: "医疗信息系统需达到等保三级",
        relevance: "系统安全建设标准",
      },
    ],
  },
];

export default function MedicalComplianceChecker() {
  const [checklist, setChecklist] = useState<ComplianceItem[]>(COMPLIANCE_CHECKLIST);
  const [activeTab, setActiveTab] = useState<"checklist" | "multisite" | "regulations">("checklist");

  const toggleCheck = (id: string) => {
    setChecklist(checklist.map(item =>
      item.id === id ? { ...item, checked: !item.checked } : item
    ));
  };

  const checkedCount = checklist.filter(i => i.checked).length;
  const requiredCount = checklist.filter(i => i.required).length;
  const requiredChecked = checklist.filter(i => i.required && i.checked).length;

  const categories = Array.from(new Set(checklist.map(i => i.category)));

  return (
    <div className="space-y-6">
      {/* 合规检查总览 */}
      <div className="rounded-lg bg-gradient-to-r from-sky-500 to-sky-600 p-4 text-white">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm opacity-90">合规检查进度</div>
            <div className="mt-1 text-2xl font-bold">
              {checkedCount}/{checklist.length} 项已检查
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm opacity-90">必选项完成</div>
            <div className={`mt-1 text-xl font-bold ${
              requiredChecked === requiredCount ? "text-emerald-300" : "text-amber-300"
            }`}>
              {requiredChecked}/{requiredCount}
            </div>
          </div>
        </div>
        <div className="mt-3 h-2 rounded-full bg-sky-800/30">
          <div
            className="h-2 rounded-full bg-white transition-all"
            style={{ width: `${(checkedCount / checklist.length) * 100}%` }}
          />
        </div>
      </div>

      {/* 标签切换 */}
      <div className="flex border-b border-slate-200 dark:border-slate-700">
        {[
          { id: "checklist", label: "合规检查清单", icon: "✓" },
          { id: "multisite", label: "多院区政策", icon: "🏥" },
          { id: "regulations", label: "法规速查", icon: "📋" },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as "checklist" | "multisite" | "regulations")}
            className={`flex items-center gap-1 px-4 py-2 text-sm font-medium ${
              activeTab === tab.id
                ? "border-b-2 border-sky-500 text-sky-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* 合规检查清单 */}
      {activeTab === "checklist" && (
        <div className="space-y-4">
          {categories.map(category => {
            const items = checklist.filter(i => i.category === category);
            const categoryChecked = items.filter(i => i.checked).length;

            return (
              <div key={category} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
                <div className="mb-3 flex items-center justify-between">
                  <h4 className="font-medium text-slate-800 dark:text-slate-200">{category}</h4>
                  <span className="text-xs text-slate-500">
                    {categoryChecked}/{items.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map(item => (
                    <label
                      key={item.id}
                      className="flex cursor-pointer items-start gap-3 rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-700/50"
                    >
                      <input
                        type="checkbox"
                        checked={item.checked}
                        onChange={() => toggleCheck(item.id)}
                        className="mt-0.5 h-4 w-4 rounded border-slate-300"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm ${item.checked ? "text-slate-500 line-through" : "text-slate-700 dark:text-slate-300"}`}>
                            {item.item}
                          </span>
                          {item.required && (
                            <span className="rounded bg-rose-100 px-1.5 py-0.5 text-xs text-rose-700">
                              必选
                            </span>
                          )}
                        </div>
                        {item.notes && (
                          <div className="mt-0.5 text-xs text-slate-500">{item.notes}</div>
                        )}
                        <div className="mt-1 text-xs text-sky-600">{item.regulation}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 多院区政策 */}
      {activeTab === "multisite" && (
        <div className="space-y-4">
          {MULTI_SITE_POLICIES.map(site => (
            <div key={site.site} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
              <h4 className="mb-3 font-medium text-slate-800 dark:text-slate-200">{site.site}</h4>
              <div className="space-y-2">
                {site.policies.map((policy, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded bg-slate-50 p-2 dark:bg-slate-700/50">
                    <div>
                      <div className="text-sm font-medium text-slate-700 dark:text-slate-300">{policy.item}</div>
                      {policy.note && (
                        <div className="text-xs text-slate-500">{policy.note}</div>
                      )}
                    </div>
                    <div className="text-sm text-sky-600">{policy.value}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div className="rounded-lg bg-amber-50 p-3 dark:bg-amber-900/20">
            <div className="text-sm text-amber-800 dark:text-amber-200">
              ⚠️ 提示：在PRD中需明确标注各院区的差异化要求
            </div>
          </div>
        </div>
      )}

      {/* 法规速查 */}
      {activeTab === "regulations" && (
        <div className="space-y-4">
          {REGULATIONS.map((reg, idx) => (
            <div key={idx} className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
              <h4 className="mb-3 font-medium text-slate-800 dark:text-slate-200">{reg.name}</h4>
              <div className="space-y-3">
                {reg.articles.map((article, aidx) => (
                  <div key={aidx} className="rounded bg-slate-50 p-3 dark:bg-slate-700/50">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700">
                        第{article.article}条
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{article.content}</p>
                    <p className="mt-1 text-xs text-slate-500">💡 {article.relevance}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

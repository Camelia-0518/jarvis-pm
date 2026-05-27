// 知识库状态管理

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface KnowledgeSection {
  id: string;
  title: string;
  content: string;
}

export interface KnowledgeDocument {
  id: string;
  title: string;
  description?: string;
  content: string;
  sections?: KnowledgeSection[];
  category: 'his' | 'insurance' | 'compliance' | 'internal';
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

interface KnowledgeState {
  documents: KnowledgeDocument[];
  recentDocuments: string[];
  searchQuery: string;
  selectedCategory: string | null;

  // Actions
  setDocuments: (docs: KnowledgeDocument[]) => void;
  addDocument: (doc: KnowledgeDocument) => void;
  updateDocument: (id: string, updates: Partial<KnowledgeDocument>) => void;
  deleteDocument: (id: string) => void;
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: string | null) => void;
  addToRecent: (docId: string) => void;
  getFilteredDocuments: () => KnowledgeDocument[];
}

// 预设文档数据
const PRESET_DOCUMENTS: KnowledgeDocument[] = [
  {
    id: 'his-standard-v3',
    title: 'HIS系统标准接口规范 V3.0',
    description: '医院信息系统接口规范，包含预约挂号、门诊缴费、病案管理等接口定义',
    content: `# HIS系统标准接口规范 V3.0

## 1. 预约挂号接口

### 1.1 获取科室列表
- **URL**: /api/his/departments
- **Method**: GET
- **Request**: None
- **Response**: Department[]

### 1.2 获取医生排班
- **URL**: /api/his/schedules
- **Method**: GET
- **Request**: { departmentId, date }
- **Response**: Schedule[]

### 1.3 预约挂号
- **URL**: /api/his/appointments
- **Method**: POST
- **Request**: { patientId, scheduleId, type }
- **Response**: { appointmentId, status }

## 2. 门诊缴费接口

### 2.1 查询待缴费列表
- **URL**: /api/his/payments/pending
- **Method**: GET
- **Request**: { patientId }
- **Response**: PaymentItem[]

### 2.2 创建支付订单
- **URL**: /api/his/payments
- **Method**: POST
- **Request**: { items, paymentMethod }
- **Response**: { orderId, payUrl }

## 3. 病案管理接口

### 3.1 查询病历列表
- **URL**: /api/his/medical-records
- **Method**: GET
- **Request**: { patientId, startDate, endDate }
- **Response**: MedicalRecord[]

### 3.2 申请病历复印
- **URL**: /api/his/medical-records/copy
- **Method**: POST
- **Request**: { recordIds, purpose, deliveryAddress }
- **Response**: { applicationId, status }`,
    category: 'his',
    tags: ['HIS', '接口规范', '预约挂号', '门诊缴费', '病案管理'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-01T00:00:00Z',
  },
  {
    id: 'insurance-policy-2024',
    title: '医保政策汇编 2024',
    description: '医保报销政策、药品目录、异地就医等相关政策',
    content: `# 医保政策汇编 2024

## 1. 基本医疗保险报销政策

### 1.1 门诊报销
- 起付线：年度累计 1800 元
- 报销比例：70%（社区医院），50%（三级医院）
- 封顶线：2 万元/年

### 1.2 住院报销
- 起付线：首次 1300 元，后续 650 元
- 报销比例：85%（三级医院），90%（二级医院），95%（社区医院）
- 封顶线：30 万元/年

## 2. 医保药品目录

### 2.1 甲类药品
- 全额纳入报销范围
- 报销比例按医院等级执行

### 2.2 乙类药品
- 个人先行自付 10%
- 剩余部分按医保政策报销

## 3. 异地就医政策

### 3.1 备案要求
- 长期异地居住：需提供居住证明
- 转诊转院：需提供转诊证明

### 3.2 报销流程
1. 办理异地就医备案
2. 在定点医院就医
3. 持医保卡直接结算
4. 未直接结算的回参保地手工报销`,
    category: 'insurance',
    tags: ['医保', '报销政策', '药品目录', '异地就医'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-01T00:00:00Z',
  },
  {
    id: 'compliance-level3',
    title: '等保三级合规要求',
    description: '信息系统安全等级保护三级合规要求清单',
    content: `# 等保三级合规要求

## 1. 安全物理环境

### 1.1 物理位置选择
- 机房应选择在具有防震、防风、防雨等能力的建筑内
- 避免设在建筑物的顶层或地下室

### 1.2 物理访问控制
- 机房出入口应配置电子门禁系统
- 控制、鉴别和记录进入的人员

## 2. 安全通信网络

### 2.1 网络架构
- 应划分不同的网络区域
- 重要网络区域应与其他区域隔离

### 2.2 通信传输
- 应采用校验技术或密码技术保证通信过程中数据的完整性
- 应采用密码技术保证通信过程中数据的保密性

## 3. 安全区域边界

### 3.1 边界防护
- 应保证跨越边界的访问和数据流通过边界设备提供的受控接口进行通信
- 应能够对非授权设备私自联到内部网络的行为进行检查或限制

### 3.2 访问控制
- 应在网络边界或区域之间根据访问控制策略设置访问控制规则
- 默认情况下除允许通信外受控接口拒绝所有通信

## 4. 安全计算环境

### 4.1 身份鉴别
- 应对登录的用户进行身份标识和鉴别
- 身份标识具有唯一性，身份鉴别信息具有复杂度要求

### 4.2 访问控制
- 应对登录的用户分配账户和权限
- 应重命名或删除默认账户，修改默认账户的默认口令

## 5. 安全管理中心

### 5.1 系统管理
- 应对系统管理员进行身份鉴别
- 应通过系统管理员对系统的资源和运行进行配置、控制和管理

### 5.2 审计管理
- 应对审计管理员进行身份鉴别
- 应通过审计管理员对审计记录进行分析，并根据分析结果进行处理`,
    category: 'compliance',
    tags: ['等保三级', '合规', '信息安全', '安全要求'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-01T00:00:00Z',
  },
  {
    id: 'multi-branch-standard',
    title: '多院区管理规范',
    description: '多院区功能分类标准、地方政策适配、数据上报要求',
    content: `# 多院区管理规范

## 1. 功能分类标准

### 1.1 标准功能
以下功能为所有院区统一标准功能：
- 用户注册/登录
- 预约挂号
- 门诊缴费
- 报告查询
- 消息推送

### 1.2 可选功能
以下功能根据院区实际情况选择开通：
- 住院服务
- 体检预约
- 互联网医院
- 药品配送

### 1.3 地方特性功能
以下功能根据地方政策定制：
- 医保支付方式
- 电子发票格式
- 健康码对接
- 当地医保政策适配

## 2. 地方政策适配

### 2.1 医保政策适配
- 各地医保报销比例差异
- 异地就医政策差异
- 特殊人群政策（如军人、老干部）

### 2.2 数据上报要求
- 各地卫健委数据上报格式
- 上报频率要求
- 数据脱敏要求

## 3. 数据同步策略

### 3.1 实时同步数据
- 用户信息
- 就诊记录
- 缴费记录

### 3.2 定时同步数据
- 统计报表
- 日志数据
- 备份数据

### 3.3 冲突解决机制
- 以总院数据为准
- 时间戳优先
- 人工审核机制`,
    category: 'internal',
    tags: ['多院区', '管理规范', '数据同步', '政策适配'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-06-01T00:00:00Z',
  },
];

export const useKnowledgeStore = create<KnowledgeState>()(
  persist(
    (set, get) => ({
      documents: PRESET_DOCUMENTS,
      recentDocuments: [],
      searchQuery: '',
      selectedCategory: null,

      setDocuments: (docs) => set({ documents: docs }),

      addDocument: (doc) =>
        set((state) => ({
          documents: [...state.documents, doc],
        })),

      updateDocument: (id, updates) =>
        set((state) => ({
          documents: state.documents.map((doc) =>
            doc.id === id ? { ...doc, ...updates, updatedAt: new Date().toISOString() } : doc
          ),
        })),

      deleteDocument: (id) =>
        set((state) => ({
          documents: state.documents.filter((doc) => doc.id !== id),
        })),

      setSearchQuery: (query) => set({ searchQuery: query }),

      setSelectedCategory: (category) => set({ selectedCategory: category }),

      addToRecent: (docId) =>
        set((state) => ({
          recentDocuments: [
            docId,
            ...state.recentDocuments.filter((id) => id !== docId),
          ].slice(0, 10),
        })),

      getFilteredDocuments: () => {
        const { documents, searchQuery, selectedCategory } = get();

        return documents.filter((doc) => {
          const matchesSearch =
            !searchQuery ||
            doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            doc.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            doc.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));

          const matchesCategory =
            !selectedCategory || doc.category === selectedCategory;

          return matchesSearch && matchesCategory;
        });
      },
    }),
    {
      name: 'aipm-knowledge',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

export default useKnowledgeStore;

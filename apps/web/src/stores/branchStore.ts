import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Branch {
  id: string;
  name: string;
  code: string;
  location: string;
  type: 'headquarters' | 'branch' | 'partner';
  parentId?: string;
  features: BranchFeature[];
  policies: BranchPolicy[];
}

export interface BranchFeature {
  id: string;
  name: string;
  category: 'standard' | 'custom';
  status: 'enabled' | 'disabled' | 'pending';
  config?: Record<string, any>;
  description?: string;
  effectiveDate?: string;
}

export interface BranchPolicy {
  id: string;
  name: string;
  type: 'medical-insurance' | 'pricing' | 'process' | 'regulation';
  content: string;
  effectiveDate: string;
  expiryDate?: string;
}

export interface FeatureComparison {
  featureName: string;
  category: 'standard' | 'custom';
  branches: {
    branchId: string;
    branchName: string;
    status: BranchFeature['status'];
    config?: Record<string, any>;
    hasDifferences: boolean;
  }[];
  isConsistent: boolean;
}

interface BranchState {
  branches: Branch[];
  selectedBranches: string[];
  comparisonView: FeatureComparison[];

  // Actions
  addBranch: (branch: Omit<Branch, 'id'>) => Branch;
  updateBranch: (id: string, updates: Partial<Branch>) => void;
  deleteBranch: (id: string) => void;
  addFeature: (branchId: string, feature: Omit<BranchFeature, 'id'>) => BranchFeature;
  updateFeature: (branchId: string, featureId: string, updates: Partial<BranchFeature>) => void;
  removeFeature: (branchId: string, featureId: string) => void;
  addPolicy: (branchId: string, policy: Omit<BranchPolicy, 'id'>) => BranchPolicy;
  toggleBranchSelection: (branchId: string) => void;
  compareBranches: (branchIds: string[]) => FeatureComparison[];
  getBranchById: (id: string) => Branch | undefined;
  getHeadquarters: () => Branch | undefined;
}

// 预设数据
const PRESET_BRANCHES: Branch[] = [
  {
    id: 'branch-hq',
    name: '集团总部',
    code: 'HQ',
    location: '北京',
    type: 'headquarters',
    features: [
      {
        id: 'f-1',
        name: '预约挂号',
        category: 'standard',
        status: 'enabled',
        description: '标准预约挂号流程',
      },
      {
        id: 'f-2',
        name: '在线支付',
        category: 'standard',
        status: 'enabled',
        description: '微信支付、支付宝',
      },
      {
        id: 'f-3',
        name: '病案复印',
        category: 'standard',
        status: 'enabled',
        description: '线上申请+快递配送',
      },
      {
        id: 'f-4',
        name: '消息推送',
        category: 'standard',
        status: 'enabled',
        description: '短信+微信+APP',
      },
      {
        id: 'f-5',
        name: '电子发票',
        category: 'standard',
        status: 'enabled',
        description: '税务Ukey对接',
      },
    ],
    policies: [
      {
        id: 'p-1',
        name: '集团标准退费政策',
        type: 'process',
        content: '退费>500元需审批',
        effectiveDate: '2024-01-01',
      },
    ],
  },
  {
    id: 'branch-jx',
    name: '江西分院',
    code: 'JX',
    location: '南昌',
    type: 'branch',
    parentId: 'branch-hq',
    features: [
      {
        id: 'f-1',
        name: '预约挂号',
        category: 'standard',
        status: 'enabled',
        description: '标准预约挂号流程',
      },
      {
        id: 'f-2',
        name: '在线支付',
        category: 'standard',
        status: 'enabled',
        config: {
          channels: ['微信支付', '支付宝', '江西医保'],
        },
        description: '包含江西医保支付',
      },
      {
        id: 'f-3',
        name: '病案复印',
        category: 'standard',
        status: 'enabled',
        description: '线上申请+快递配送',
      },
      {
        id: 'f-4',
        name: '消息推送',
        category: 'standard',
        status: 'enabled',
        config: {
          channels: ['短信', '微信', '赣服通'],
        },
        description: '对接赣服通',
      },
      {
        id: 'f-5',
        name: '电子发票',
        category: 'standard',
        status: 'enabled',
        description: '税务Ukey对接',
      },
      {
        id: 'f-jx-1',
        name: '中药房管理',
        category: 'custom',
        status: 'enabled',
        description: '江西特色中药房',
      },
      {
        id: 'f-jx-2',
        name: '赣服通入口',
        category: 'custom',
        status: 'enabled',
        description: '江西政务服务网入口',
      },
    ],
    policies: [
      {
        id: 'p-jx-1',
        name: '江西省医保政策',
        type: 'medical-insurance',
        content: '执行江西省医保报销比例',
        effectiveDate: '2024-01-01',
      },
      {
        id: 'p-jx-2',
        name: '中药处方规范',
        type: 'regulation',
        content: '中药处方特殊管理要求',
        effectiveDate: '2024-01-01',
      },
    ],
  },
  {
    id: 'branch-lx',
    name: '临夏分院',
    code: 'LX',
    location: '临夏',
    type: 'branch',
    parentId: 'branch-hq',
    features: [
      {
        id: 'f-1',
        name: '预约挂号',
        category: 'standard',
        status: 'enabled',
        description: '标准预约挂号流程',
      },
      {
        id: 'f-2',
        name: '在线支付',
        category: 'standard',
        status: 'enabled',
        config: {
          channels: ['微信支付', '支付宝', '甘肃医保'],
        },
        description: '包含甘肃医保支付',
      },
      {
        id: 'f-3',
        name: '病案复印',
        category: 'standard',
        status: 'enabled',
        description: '线上申请+快递配送',
      },
      {
        id: 'f-4',
        name: '消息推送',
        category: 'standard',
        status: 'enabled',
        description: '短信+微信+APP',
      },
      {
        id: 'f-5',
        name: '电子发票',
        category: 'standard',
        status: 'pending',
        description: '税务Ukey对接中',
      },
      {
        id: 'f-lx-1',
        name: '远程会诊',
        category: 'custom',
        status: 'enabled',
        config: {
          priority: 'high',
        },
        description: '远程会诊优先通道',
      },
      {
        id: 'f-lx-2',
        name: '多语言支持',
        category: 'custom',
        status: 'enabled',
        description: '支持少数民族语言',
      },
    ],
    policies: [
      {
        id: 'p-lx-1',
        name: '甘肃省医保政策',
        type: 'medical-insurance',
        content: '执行甘肃省医保报销比例',
        effectiveDate: '2024-01-01',
      },
      {
        id: 'p-lx-2',
        name: '远程医疗补贴',
        type: 'pricing',
        content: '远程会诊享受政府补贴',
        effectiveDate: '2024-01-01',
      },
    ],
  },
  {
    id: 'branch-zj',
    name: '浙江分院',
    code: 'ZJ',
    location: '杭州',
    type: 'branch',
    parentId: 'branch-hq',
    features: [
      {
        id: 'f-1',
        name: '预约挂号',
        category: 'standard',
        status: 'enabled',
        description: '标准预约挂号流程',
      },
      {
        id: 'f-2',
        name: '在线支付',
        category: 'standard',
        status: 'enabled',
        config: {
          channels: ['微信支付', '支付宝', '浙江医保'],
        },
        description: '包含浙江医保支付',
      },
      {
        id: 'f-3',
        name: '病案复印',
        category: 'standard',
        status: 'enabled',
        description: '线上申请+快递配送',
      },
      {
        id: 'f-4',
        name: '消息推送',
        category: 'standard',
        status: 'enabled',
        config: {
          channels: ['短信', '微信', '浙里办'],
        },
        description: '对接浙里办',
      },
      {
        id: 'f-5',
        name: '电子发票',
        category: 'standard',
        status: 'enabled',
        description: '税务Ukey对接',
      },
      {
        id: 'f-zj-1',
        name: '互联网医院',
        category: 'custom',
        status: 'enabled',
        description: '浙江互联网医院资质',
      },
      {
        id: 'f-zj-2',
        name: '电子健康卡',
        category: 'custom',
        status: 'enabled',
        description: '对接浙江电子健康卡',
      },
    ],
    policies: [
      {
        id: 'p-zj-1',
        name: '浙江省医保政策',
        type: 'medical-insurance',
        content: '执行浙江省医保报销比例',
        effectiveDate: '2024-01-01',
      },
      {
        id: 'p-zj-2',
        name: '互联网医院管理办法',
        type: 'regulation',
        content: '浙江省互联网医院管理规范',
        effectiveDate: '2024-01-01',
      },
    ],
  },
];

export const useBranchStore = create<BranchState>()(
  persist(
    (set, get) => ({
      branches: PRESET_BRANCHES,
      selectedBranches: [],
      comparisonView: [],

      addBranch: (branch) => {
        const newBranch: Branch = {
          ...branch,
          id: `branch-${Date.now()}`,
        };
        set((state) => ({
          branches: [...state.branches, newBranch],
        }));
        return newBranch;
      },

      updateBranch: (id, updates) => {
        set((state) => ({
          branches: state.branches.map((b) =>
            b.id === id ? { ...b, ...updates } : b
          ),
        }));
      },

      deleteBranch: (id) => {
        set((state) => ({
          branches: state.branches.filter((b) => b.id !== id),
        }));
      },

      addFeature: (branchId, feature) => {
        const newFeature: BranchFeature = {
          ...feature,
          id: `f-${Date.now()}`,
        };
        set((state) => ({
          branches: state.branches.map((b) =>
            b.id === branchId
              ? { ...b, features: [...b.features, newFeature] }
              : b
          ),
        }));
        return newFeature;
      },

      updateFeature: (branchId, featureId, updates) => {
        set((state) => ({
          branches: state.branches.map((b) =>
            b.id === branchId
              ? {
                  ...b,
                  features: b.features.map((f) =>
                    f.id === featureId ? { ...f, ...updates } : f
                  ),
                }
              : b
          ),
        }));
      },

      removeFeature: (branchId, featureId) => {
        set((state) => ({
          branches: state.branches.map((b) =>
            b.id === branchId
              ? { ...b, features: b.features.filter((f) => f.id !== featureId) }
              : b
          ),
        }));
      },

      addPolicy: (branchId, policy) => {
        const newPolicy: BranchPolicy = {
          ...policy,
          id: `p-${Date.now()}`,
        };
        set((state) => ({
          branches: state.branches.map((b) =>
            b.id === branchId
              ? { ...b, policies: [...b.policies, newPolicy] }
              : b
          ),
        }));
        return newPolicy;
      },

      toggleBranchSelection: (branchId) => {
        set((state) => {
          const isSelected = state.selectedBranches.includes(branchId);
          const selectedBranches = isSelected
            ? state.selectedBranches.filter((id) => id !== branchId)
            : [...state.selectedBranches, branchId];
          return { selectedBranches };
        });
      },

      compareBranches: (branchIds) => {
        const branches = get().branches.filter((b) => branchIds.includes(b.id));
        const allFeatureNames = new Set<string>();

        // Collect all feature names
        branches.forEach((branch) => {
          branch.features.forEach((f) => allFeatureNames.add(f.name));
        });

        // Build comparison view
        const comparison: FeatureComparison[] = Array.from(allFeatureNames).map(
          (featureName) => {
            const featureInstances = branches.map((branch) => {
              const feature = branch.features.find((f) => f.name === featureName);
              return {
                branchId: branch.id,
                branchName: branch.name,
                status: feature?.status || 'disabled',
                config: feature?.config,
                hasDifferences: false,
              };
            });

            // Check for differences
            const firstEnabled = featureInstances.find(
              (f) => f.status === 'enabled'
            );
            const hasDifferences = featureInstances.some(
              (f) =>
                f.status !== firstEnabled?.status ||
                JSON.stringify(f.config) !== JSON.stringify(firstEnabled?.config)
            );

            featureInstances.forEach((f) => {
              f.hasDifferences = hasDifferences;
            });

            // Determine category based on first found feature
            const firstFeature = branches
              .flatMap((b) => b.features)
              .find((f) => f.name === featureName);

            return {
              featureName,
              category: firstFeature?.category || 'standard',
              branches: featureInstances,
              isConsistent: !hasDifferences,
            };
          }
        );

        set({ comparisonView: comparison });
        return comparison;
      },

      getBranchById: (id) => {
        return get().branches.find((b) => b.id === id);
      },

      getHeadquarters: () => {
        return get().branches.find((b) => b.type === 'headquarters');
      },
    }),
    {
      name: 'branch-store',
    }
  )
);

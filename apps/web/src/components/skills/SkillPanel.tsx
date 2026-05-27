// 技能面板组件
// 展示技能列表、执行表单和结果

'use client';

import { useState, useCallback } from 'react';
import {
  Search,
  Play,
  History,
  Star,
  Clock,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Zap,
  Filter,
} from 'lucide-react';
import { useSkillStore } from '@/stores/skillStore';
import {
  skillRegistry,
  SKILL_CATEGORIES,
  AGENT_SKILL_MAP,
} from '@/services/skills/registry';
import type { SkillDefinition, SkillParameter } from '@/types/skill';
import type { AgentRole } from '@/types/agent';
import { Button } from '@/components/ui-from-ai-pm/button';
import { Input } from '@/components/ui-from-ai-pm/input';
import { Textarea } from '@/components/ui-from-ai-pm/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui-from-ai-pm/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui-from-ai-pm/card';
import { Badge } from '@/components/ui-from-ai-pm/badge';
import { ScrollArea } from '@/components/ui-from-ai-pm/scroll-area';
import { Separator } from '@/components/ui-from-ai-pm/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui-from-ai-pm/dialog';
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/components/ui-from-ai-pm/alert';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface SkillPanelProps {
  agentRole?: AgentRole | string;
  projectId?: string;
  conversationId?: string;
}

export function SkillPanel({ agentRole, projectId, conversationId }: SkillPanelProps) {
  // Store state
  const {
    selectedSkill,
    setSelectedSkill,
    skillInputs,
    setSkillInput,
    setSkillInputs,
    resetSkillInputs,
    executeSkill,
    isExecuting,
    currentExecution,
    executionHistory,
    filterRole,
    filterCategory,
    searchQuery,
    setFilterRole,
    setFilterCategory,
    setSearchQuery,
    clearFilters,
    recentSkills,
    favoriteSkills,
    toggleFavoriteSkill,
    toggleExecutionExpand,
    getFilteredSkills,
    getSkillHistory,
    error,
  } = useSkillStore();

  // Local state
  const [showHistory, setShowHistory] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'recent' | 'favorite'>('all');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Get skills based on current filters
  const allSkills = getFilteredSkills();

  // Filter by agent role if specified
  const filteredSkills = agentRole
    ? allSkills.filter((skill) => skill.agentRole === agentRole)
    : allSkills;

  // Get recent and favorite skills
  const recentSkillList = recentSkills
    .map((id) => skillRegistry.getSkillById(id))
    .filter(Boolean) as SkillDefinition[];

  const favoriteSkillList = favoriteSkills
    .map((id) => skillRegistry.getSkillById(id))
    .filter(Boolean) as SkillDefinition[];

  // Get skills for current tab
  const displaySkills =
    activeTab === 'recent'
      ? recentSkillList
      : activeTab === 'favorite'
        ? favoriteSkillList
        : filteredSkills;

  // Get current skill history
  const skillHistory = selectedSkill ? getSkillHistory(selectedSkill.id) : [];

  // Handle skill selection
  const handleSelectSkill = useCallback(
    (skill: SkillDefinition) => {
      setSelectedSkill(skill);
      setValidationErrors({});

      // Initialize inputs with defaults if not already set
      const currentInputs = skillInputs[skill.id] || {};
      if (Object.keys(currentInputs).length === 0) {
        const defaults: Record<string, unknown> = {};
        skill.parameters.forEach((param) => {
          if (param.defaultValue !== undefined) {
            defaults[param.name] = param.defaultValue;
          }
        });
        setSkillInputs(skill.id, defaults);
      }
    },
    [setSelectedSkill, skillInputs, setSkillInputs]
  );

  // Handle input change
  const handleInputChange = (paramName: string, value: unknown) => {
    if (selectedSkill) {
      setSkillInput(selectedSkill.id, paramName, value);
      // Clear validation error for this field
      if (validationErrors[paramName]) {
        setValidationErrors((prev) => {
          const next = { ...prev };
          delete next[paramName];
          return next;
        });
      }
    }
  };

  // Validate form
  const validateForm = (): boolean => {
    if (!selectedSkill) return false;

    const errors: Record<string, string> = {};
    const inputs = skillInputs[selectedSkill.id] || {};

    selectedSkill.parameters.forEach((param) => {
      if (
        param.required &&
        (inputs[param.name] === undefined || inputs[param.name] === '')
      ) {
        errors[param.name] = `${param.label} 是必填项`;
      }
    });

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle execute
  const handleExecute = async () => {
    if (!selectedSkill || !validateForm()) return;

    const inputs = skillInputs[selectedSkill.id] || {};
    await executeSkill(selectedSkill.id, inputs, {
      projectId,
      conversationId,
    });
  };

  // Render input field based on parameter type
  const renderInputField = (param: SkillParameter) => {
    const value = selectedSkill ? skillInputs[selectedSkill.id]?.[param.name] : '';
    const error = validationErrors[param.name];

    const baseProps = {
      id: param.name,
      placeholder: param.placeholder,
      className: error ? 'border-rose-500' : '',
    };

    switch (param.type) {
      case 'textarea':
        return (
          <Textarea
            {...baseProps}
            value={(value as string) || ''}
            onChange={(e) => handleInputChange(param.name, e.target.value)}
            rows={4}
          />
        );

      case 'select':
        return (
          <Select
            value={(value as string) || ''}
            onValueChange={(val) => handleInputChange(param.name, val)}
          >
            <SelectTrigger className={error ? 'border-rose-500' : ''}>
              <SelectValue placeholder={`选择 ${param.label}`} />
            </SelectTrigger>
            <SelectContent>
              {param.options?.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'boolean':
        return (
          <Select
            value={value ? 'true' : 'false'}
            onValueChange={(val) => handleInputChange(param.name, val === 'true')}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">是</SelectItem>
              <SelectItem value="false">否</SelectItem>
            </SelectContent>
          </Select>
        );

      case 'number':
        return (
          <Input
            {...baseProps}
            type="number"
            value={(value as number) || ''}
            onChange={(e) =>
              handleInputChange(param.name, parseFloat(e.target.value))
            }
            min={param.min}
            max={param.max}
          />
        );

      case 'array':
        return (
          <Textarea
            {...baseProps}
            value={Array.isArray(value) ? value.join('\n') : ''}
            onChange={(e) =>
              handleInputChange(
                param.name,
                e.target.value.split('\n').filter((v) => v.trim())
              )
            }
            rows={3}
            placeholder={`${param.placeholder || ''} (每行一个)`}
          />
        );

      default:
        return (
          <Input
            {...baseProps}
            type="text"
            value={(value as string) || ''}
            onChange={(e) => handleInputChange(param.name, e.target.value)}
          />
        );
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-3">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" />
          <h3 className="font-semibold">技能面板</h3>
          <Badge variant="secondary" className="text-xs">
            {filteredSkills.length}
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setShowHistory(!showHistory)}
            title="执行历史"
          >
            <History className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Skill List */}
        <div
          className={`flex flex-col border-r ${selectedSkill ? 'w-64' : 'flex-1'}`}
        >
          {/* Search & Filter */}
          <div className="space-y-2 border-b p-3">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索技能..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs"
              />
            </div>

            {/* Category Filter */}
            <div className="flex flex-wrap gap-1">
              {SKILL_CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  onClick={() =>
                    setFilterCategory(
                      filterCategory === cat.value ? null : cat.value
                    )
                  }
                  className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] transition-colors ${
                    filterCategory === cat.value
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted hover:bg-muted/80'
                  }`}
                >
                  <span>{cat.icon}</span>
                  <span>{cat.label}</span>
                </button>
              ))}
            </div>

            {/* Tabs */}
            <div className="flex gap-1">
              {(['all', 'recent', 'favorite'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 rounded px-2 py-1 text-[10px] font-medium transition-colors ${
                    activeTab === tab
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  {tab === 'all' && '全部'}
                  {tab === 'recent' && '最近'}
                  {tab === 'favorite' && '收藏'}
                </button>
              ))}
            </div>
          </div>

          {/* Skill List */}
          <ScrollArea className="flex-1">
            <div className="space-y-1 p-2">
              {displaySkills.map((skill) => {
                const isSelected = selectedSkill?.id === skill.id;
                const isFavorite = favoriteSkills.includes(skill.id);

                return (
                  <button
                    key={skill.id}
                    onClick={() => handleSelectSkill(skill)}
                    className={`w-full rounded-md border p-2 text-left transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50 hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{skill.icon || '🔧'}</span>
                        <span className="text-xs font-medium">{skill.name}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleFavoriteSkill(skill.id);
                        }}
                        className="text-muted-foreground hover:text-amber-500"
                      >
                        <Star
                          className={`h-3 w-3 ${
                            isFavorite ? 'fill-amber-500 text-amber-500' : ''
                          }`}
                        />
                      </button>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[10px] text-muted-foreground">
                      {skill.description}
                    </p>
                    <div className="mt-2 flex items-center gap-1">
                      {skill.tags?.slice(0, 3).map((tag) => (
                        <Badge
                          key={tag}
                          variant="outline"
                          className="text-[8px] px-1 py-0"
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </button>
                );
              })}

              {displaySkills.length === 0 && (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  暂无技能
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right: Skill Detail / Execution Form */}
        {selectedSkill && (
          <div className="flex-1 flex flex-col">
            <ScrollArea className="flex-1">
              <div className="space-y-4 p-4">
                {/* Skill Info */}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{selectedSkill.icon}</span>
                    <div>
                      <h4 className="font-semibold">{selectedSkill.name}</h4>
                      <p className="text-xs text-muted-foreground">
                        {selectedSkill.description}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Examples */}
                {selectedSkill.examples && selectedSkill.examples.length > 0 && (
                  <div>
                    <label className="text-xs font-medium">快速示例</label>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {selectedSkill.examples.map((example) => (
                        <button
                          key={example.id}
                          onClick={() => {
                            setSkillInputs(selectedSkill.id, example.inputs);
                          }}
                          className="rounded border px-2 py-1 text-[10px] hover:bg-muted"
                        >
                          {example.name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <Separator />

                {/* Execution Form */}
                <div className="space-y-3">
                  <h5 className="text-xs font-medium">执行参数</h5>

                  {selectedSkill.parameters.map((param) => (
                    <div key={param.name}>
                      <label className="flex items-center gap-1 text-xs">
                        {param.label}
                        {param.required && (
                          <span className="text-rose-500">*</span>
                        )}
                      </label>
                      <div className="mt-1">
                        {renderInputField(param)}
                        {param.description && (
                          <p className="mt-0.5 text-[10px] text-muted-foreground">
                            {param.description}
                          </p>
                        )}
                        {validationErrors[param.name] && (
                          <p className="mt-0.5 text-[10px] text-rose-500">
                            {validationErrors[param.name]}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Execute Button */}
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleExecute}
                    disabled={isExecuting}
                    className="flex-1"
                    size="sm"
                  >
                    {isExecuting ? (
                      <>
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        执行中...
                      </>
                    ) : (
                      <>
                        <Play className="mr-1 h-3 w-3" />
                        执行技能
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => resetSkillInputs(selectedSkill.id)}
                  >
                    重置
                  </Button>
                </div>

                {/* Error Display */}
                {error && (
                  <Alert variant="destructive" className="text-xs">
                    <AlertCircle className="h-3 w-3" />
                    <AlertTitle>执行失败</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Current Execution Result */}
                {currentExecution && (
                  <div className="rounded-md border">
                    <div className="flex items-center justify-between border-b bg-muted/50 px-3 py-2">
                      <div className="flex items-center gap-2">
                        {currentExecution.status === 'completed' ? (
                          <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
                        ) : currentExecution.status === 'failed' ? (
                          <XCircle className="h-3.5 w-3.5 text-rose-500" />
                        ) : (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        )}
                        <span className="text-xs font-medium">
                          {currentExecution.status === 'completed'
                            ? '执行完成'
                            : currentExecution.status === 'failed'
                              ? '执行失败'
                              : '执行中...'}
                        </span>
                      </div>
                      {currentExecution.executionTime && (
                        <span className="text-[10px] text-muted-foreground">
                          {currentExecution.executionTime}ms
                        </span>
                      )}
                    </div>
                    <div className="p-3">
                      {currentExecution.formattedOutput ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {currentExecution.formattedOutput}
                          </ReactMarkdown>
                        </div>
                      ) : currentExecution.output ? (
                        <pre className="max-h-64 overflow-auto rounded bg-muted p-2 text-[10px]">
                          {JSON.stringify(currentExecution.output, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          等待执行结果...
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Skill History */}
                {skillHistory.length > 0 && (
                  <div>
                    <h5 className="mb-2 text-xs font-medium">历史执行</h5>
                    <div className="space-y-2">
                      {skillHistory.slice(0, 3).map((record) => (
                        <div
                          key={record.id}
                          className="rounded border p-2 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-muted-foreground">
                              {new Date(record.createdAt).toLocaleString()}
                            </span>
                            <Badge
                              variant={
                                record.status === 'completed'
                                  ? 'default'
                                  : record.status === 'failed'
                                    ? 'destructive'
                                    : 'secondary'
                              }
                              className="text-[8px]"
                            >
                              {record.status === 'completed'
                                ? '完成'
                                : record.status === 'failed'
                                  ? '失败'
                                  : '运行中'}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* History Panel (Slide over) */}
        {showHistory && (
          <div className="w-72 border-l bg-background">
            <div className="flex items-center justify-between border-b p-3">
              <h4 className="text-xs font-semibold">执行历史</h4>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setShowHistory(false)}
              >
                <span className="text-xs">✕</span>
              </Button>
            </div>
            <ScrollArea className="h-[calc(100%-40px)]">
              <div className="space-y-2 p-2">
                {executionHistory.length === 0 ? (
                  <div className="py-8 text-center text-xs text-muted-foreground">
                    暂无执行记录
                  </div>
                ) : (
                  executionHistory.map((record) => (
                    <div
                      key={record.id}
                      className="rounded border p-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">{record.skillName}</span>
                        <button
                          onClick={() => toggleExecutionExpand(record.id)}
                        >
                          {record.isExpanded ? (
                            <ChevronUp className="h-3 w-3" />
                          ) : (
                            <ChevronDown className="h-3 w-3" />
                          )}
                        </button>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>
                          {new Date(record.createdAt).toLocaleString()}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-1">
                        <Badge
                          variant={
                            record.status === 'completed'
                              ? 'default'
                              : record.status === 'failed'
                                ? 'destructive'
                                : 'secondary'
                          }
                          className="text-[8px]"
                        >
                          {record.status === 'completed'
                            ? '完成'
                            : record.status === 'failed'
                              ? '失败'
                              : '运行中'}
                        </Badge>
                        {record.executionTime && (
                          <span className="text-[8px] text-muted-foreground">
                            {record.executionTime}ms
                          </span>
                        )}
                      </div>

                      {record.isExpanded && record.output && (
                        <div className="mt-2 max-h-32 overflow-auto rounded bg-muted p-1.5">
                          <pre className="text-[8px]">
                            {JSON.stringify(record.output, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  );
}

export default SkillPanel;

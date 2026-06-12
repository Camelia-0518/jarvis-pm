"use client";

import { useState, useEffect } from "react";
import { confirm } from "@/components/ui/ConfirmDialog";

interface ReviewOpinion {
  id: string;
  chapterNum: string;
  chapterTitle: string;
  content: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'modified' | 'confirmed';
  reviewer: string;
}

interface ReviewMeeting {
  id: string;
  title: string;
  date: string;
  participants: string[];
  opinions: ReviewOpinion[];
  status: 'open' | 'closed';
  createdAt: string;
}

interface Props {
  prdId: string;
  chapters: { num: string; title: string }[];
}

const PRIORITY_LABELS: Record<string, { text: string; color: string }> = {
  high: { text: '高', color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400' },
  medium: { text: '中', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' },
  low: { text: '低', color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400' },
};

const STATUS_LABELS: Record<string, { text: string; color: string }> = {
  pending: { text: '待处理', color: 'text-amber-600 dark:text-amber-400' },
  modified: { text: '已修改', color: 'text-sky-600 dark:text-sky-400' },
  confirmed: { text: '已确认', color: 'text-emerald-600 dark:text-emerald-400' },
};

function getStorageKey(prdId: string) {
  return `review-meetings-${prdId}`;
}

export default function ReviewMeetingPanel({ prdId, chapters }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [meetings, setMeetings] = useState<ReviewMeeting[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showAddOpinion, setShowAddOpinion] = useState<string | null>(null);
  const [selectedMeeting, setSelectedMeeting] = useState<string | null>(null);

  const [newMeeting, setNewMeeting] = useState({
    title: '',
    date: new Date().toISOString().split('T')[0],
    participants: '',
  });

  const [newOpinion, setNewOpinion] = useState({
    chapterNum: '',
    content: '',
    priority: 'medium' as 'high' | 'medium' | 'low',
    reviewer: '',
  });

  useEffect(() => {
    const key = getStorageKey(prdId);
    const saved = localStorage.getItem(key);
    if (saved) {
      try { setMeetings(JSON.parse(saved)); } catch { /* ignore */ }
    }
  }, [prdId]);

  const persist = (next: ReviewMeeting[]) => {
    setMeetings(next);
    localStorage.setItem(getStorageKey(prdId), JSON.stringify(next));
  };

  const handleCreateMeeting = () => {
    if (!newMeeting.title.trim()) return;
    const meeting: ReviewMeeting = {
      id: `rm_${Date.now()}`,
      title: newMeeting.title.trim(),
      date: newMeeting.date,
      participants: newMeeting.participants.split(',').map(s => s.trim()).filter(Boolean),
      opinions: [],
      status: 'open',
      createdAt: new Date().toISOString(),
    };
    persist([meeting, ...meetings]);
    setShowCreateForm(false);
    setNewMeeting({ title: '', date: new Date().toISOString().split('T')[0], participants: '' });
  };

  const handleAddOpinion = (meetingId: string) => {
    if (!newOpinion.content.trim() || !newOpinion.chapterNum) return;
    const ch = chapters.find(c => c.num === newOpinion.chapterNum);
    const next = meetings.map(m => {
      if (m.id !== meetingId) return m;
      return {
        ...m,
        opinions: [...m.opinions, {
          id: `op_${Date.now()}`,
          chapterNum: newOpinion.chapterNum,
          chapterTitle: ch?.title || '',
          content: newOpinion.content.trim(),
          priority: newOpinion.priority,
          status: 'pending' as const,
          reviewer: newOpinion.reviewer.trim() || '评审人',
        }],
      };
    });
    persist(next);
    setShowAddOpinion(null);
    setNewOpinion({ chapterNum: '', content: '', priority: 'medium', reviewer: '' });
  };

  const handleUpdateOpinionStatus = (meetingId: string, opinionId: string, status: ReviewOpinion['status']) => {
    const next = meetings.map(m => {
      if (m.id !== meetingId) return m;
      return {
        ...m,
        opinions: m.opinions.map(o => o.id === opinionId ? { ...o, status } : o),
      };
    });
    persist(next);
  };

  const handleCloseMeeting = async (meetingId: string) => {
    const confirmed = await confirm({
      title: '关闭评审会议',
      message: '关闭后不能再添加评审意见，确定继续吗？',
      type: 'warning',
    });
    if (!confirmed) return;
    const next = meetings.map(m => m.id === meetingId ? { ...m, status: 'closed' as const } : m);
    persist(next);
  };

  const handleDeleteMeeting = async (meetingId: string) => {
    const confirmed = await confirm({
      title: '删除评审会议',
      message: '此操作不可恢复，确定删除吗？',
      type: 'danger',
    });
    if (!confirmed) return;
    persist(meetings.filter(m => m.id !== meetingId));
    if (selectedMeeting === meetingId) setSelectedMeeting(null);
  };

  const activeMeetings = meetings.filter(m => m.status === 'open');
  const closedMeetings = meetings.filter(m => m.status === 'closed');

  return (
    <div className="mt-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="mb-1 flex w-full items-center justify-between px-2.5 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
      >
        <span className="flex items-center gap-1.5">
          评审会议
          {activeMeetings.length > 0 && (
            <span className="rounded-full bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
              {activeMeetings.length}
            </span>
          )}
        </span>
        <span>{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div className="space-y-2 px-2.5">
          {/* Create button */}
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="w-full rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-violet-700"
          >
            {showCreateForm ? '取消' : '+ 新建评审会议'}
          </button>

          {/* Create form */}
          {showCreateForm && (
            <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-800">
              <input
                value={newMeeting.title}
                onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                placeholder="会议主题"
                className="w-full rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
              />
              <input
                type="date"
                value={newMeeting.date}
                onChange={(e) => setNewMeeting({ ...newMeeting, date: e.target.value })}
                className="w-full rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
              />
              <input
                value={newMeeting.participants}
                onChange={(e) => setNewMeeting({ ...newMeeting, participants: e.target.value })}
                placeholder="参与人（用逗号分隔）"
                className="w-full rounded border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
              />
              <button
                onClick={handleCreateMeeting}
                disabled={!newMeeting.title.trim()}
                className="w-full rounded bg-violet-500 px-2 py-1 text-[11px] font-medium text-white hover:bg-violet-600 disabled:opacity-50"
              >
                创建
              </button>
            </div>
          )}

          {/* Meetings list */}
          {meetings.length === 0 ? (
            <div className="py-2 text-xs text-slate-400">暂无评审会议</div>
          ) : (
            <div className="space-y-2">
              {[...activeMeetings, ...closedMeetings].map((m) => {
                const pendingCount = m.opinions.filter(o => o.status === 'pending').length;
                const isSelected = selectedMeeting === m.id;
                return (
                  <div key={m.id} className="rounded-lg border border-slate-200 dark:border-slate-700">
                    <div
                      onClick={() => setSelectedMeeting(isSelected ? null : m.id)}
                      className="cursor-pointer px-2.5 py-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{m.title}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${m.status === 'open' ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400' : 'bg-slate-100 text-slate-500 dark:bg-slate-700'}`}>
                          {m.status === 'open' ? '进行中' : '已关闭'}
                        </span>
                      </div>
                      <div className="mt-0.5 flex items-center gap-2 text-[10px] text-slate-400">
                        <span>{m.date}</span>
                        <span>·</span>
                        <span>{m.opinions.length} 条意见</span>
                        {pendingCount > 0 && m.status === 'open' && (
                          <span className="rounded bg-amber-100 px-1 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                            {pendingCount} 待处理
                          </span>
                        )}
                      </div>
                      {m.participants.length > 0 && (
                        <div className="mt-0.5 text-[10px] text-slate-400">
                          参与人: {m.participants.join('、')}
                        </div>
                      )}
                    </div>

                    {/* Meeting detail */}
                    {isSelected && (
                      <div className="border-t border-slate-100 px-2.5 py-2 dark:border-slate-700">
                        {/* Opinions */}
                        {m.opinions.length === 0 ? (
                          <div className="py-1 text-[11px] text-slate-400">暂无评审意见</div>
                        ) : (
                          <div className="space-y-1.5">
                            {m.opinions.map((op) => (
                              <div key={op.id} className="rounded bg-slate-50 p-1.5 dark:bg-slate-800">
                                <div className="flex items-center gap-1.5 mb-0.5">
                                  <span className={`rounded px-1 py-0.5 text-[10px] font-medium ${PRIORITY_LABELS[op.priority].color}`}>
                                    {PRIORITY_LABELS[op.priority].text}
                                  </span>
                                  <span className="text-[10px] text-slate-500">{op.chapterNum} {op.chapterTitle}</span>
                                  <span className={`ml-auto text-[10px] font-medium ${STATUS_LABELS[op.status].color}`}>
                                    {STATUS_LABELS[op.status].text}
                                  </span>
                                </div>
                                <p className="text-[11px] text-slate-700 dark:text-slate-300">{op.content}</p>
                                <div className="mt-1 flex items-center justify-between">
                                  <span className="text-[10px] text-slate-400">{op.reviewer}</span>
                                  {m.status === 'open' && (
                                    <div className="flex gap-1">
                                      {op.status !== 'modified' && (
                                        <button
                                          onClick={() => handleUpdateOpinionStatus(m.id, op.id, 'modified')}
                                          className="rounded bg-sky-50 px-1.5 py-0.5 text-[10px] text-sky-700 hover:bg-sky-100 dark:bg-sky-900/20 dark:text-sky-400"
                                        >
                                          标记已修改
                                        </button>
                                      )}
                                      {op.status !== 'confirmed' && (
                                        <button
                                          onClick={() => handleUpdateOpinionStatus(m.id, op.id, 'confirmed')}
                                          className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400"
                                        >
                                          确认
                                        </button>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Add opinion form */}
                        {m.status === 'open' && (
                          <div className="mt-2">
                            {showAddOpinion === m.id ? (
                              <div className="space-y-1.5 rounded border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-800">
                                <select
                                  value={newOpinion.chapterNum}
                                  onChange={(e) => setNewOpinion({ ...newOpinion, chapterNum: e.target.value })}
                                  className="w-full rounded border border-slate-200 bg-white px-2 py-1 text-[11px] dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
                                >
                                  <option value="">选择章节</option>
                                  {chapters.map((ch) => (
                                    <option key={ch.num} value={ch.num}>{ch.num}. {ch.title}</option>
                                  ))}
                                </select>
                                <textarea
                                  value={newOpinion.content}
                                  onChange={(e) => setNewOpinion({ ...newOpinion, content: e.target.value })}
                                  placeholder="评审意见"
                                  rows={2}
                                  className="w-full resize-none rounded border border-slate-200 bg-white px-2 py-1 text-[11px] dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
                                />
                                <div className="flex gap-1">
                                  <select
                                    value={newOpinion.priority}
                                    onChange={(e) => setNewOpinion({ ...newOpinion, priority: e.target.value as 'high' | 'medium' | 'low' })}
                                    className="rounded border border-slate-200 bg-white px-2 py-1 text-[11px] dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
                                  >
                                    <option value="high">高优先级</option>
                                    <option value="medium">中优先级</option>
                                    <option value="low">低优先级</option>
                                  </select>
                                  <input
                                    value={newOpinion.reviewer}
                                    onChange={(e) => setNewOpinion({ ...newOpinion, reviewer: e.target.value })}
                                    placeholder="评审人"
                                    className="flex-1 rounded border border-slate-200 bg-white px-2 py-1 text-[11px] dark:border-slate-600 dark:bg-slate-700 dark:text-slate-300"
                                  />
                                </div>
                                <div className="flex gap-1">
                                  <button
                                    onClick={() => handleAddOpinion(m.id)}
                                    disabled={!newOpinion.content.trim() || !newOpinion.chapterNum}
                                    className="flex-1 rounded bg-violet-500 px-2 py-1 text-[11px] font-medium text-white hover:bg-violet-600 disabled:opacity-50"
                                  >
                                    添加
                                  </button>
                                  <button
                                    onClick={() => setShowAddOpinion(null)}
                                    className="rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-600 dark:border-slate-600 dark:text-slate-300"
                                  >
                                    取消
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button
                                onClick={() => setShowAddOpinion(m.id)}
                                className="w-full rounded-md bg-violet-50 px-2 py-1 text-[11px] font-medium text-violet-700 transition-colors hover:bg-violet-100 dark:bg-violet-900/20 dark:text-violet-400"
                              >
                                + 添加评审意见
                              </button>
                            )}
                          </div>
                        )}

                        {/* Actions */}
                        {m.status === 'open' && (
                          <div className="mt-2 flex gap-1">
                            <button
                              onClick={() => handleCloseMeeting(m.id)}
                              className="flex-1 rounded border border-slate-200 px-2 py-1 text-[11px] text-slate-600 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300"
                            >
                              关闭会议
                            </button>
                          </div>
                        )}
                        <button
                          onClick={() => handleDeleteMeeting(m.id)}
                          className="mt-1 w-full rounded px-2 py-1 text-[11px] text-rose-600 hover:bg-rose-50 dark:text-rose-400"
                        >
                          删除
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import NavHeader from "@/components/global/NavHeader";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { workspaceApi, type WorkspaceMember } from "@/lib/api";
import { toast } from "sonner";

type TabId = "general" | "members";

export default function WorkspaceSettingsPage() {
  const { workspaces, activeWorkspaceId, fetchWorkspaces, setActiveWorkspace } = useWorkspaceStore();
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [tab, setTab] = useState<TabId>("general");
  const [hydrated, setHydrated] = useState(false);

  // Create form
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchWorkspaces().then(() => setHydrated(true));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const activeWs = workspaces.find((w) => w.workspace_id === activeWorkspaceId) || null;

  const fetchMembers = async (wsId: string) => {
    try {
      const list = await workspaceApi.getMembers(wsId);
      setMembers(list);
    } catch { /* */ }
  };

  useEffect(() => {
    if (activeWorkspaceId) fetchMembers(activeWorkspaceId);
  }, [activeWorkspaceId]);

  const handleCreate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newName.trim() || !newSlug.trim()) {
      toast.error("请填写名称和 slug");
      return;
    }
    setCreating(true);
    try {
      const ws = await workspaceApi.create({ name: newName.trim(), slug: newSlug.trim().toLowerCase() });
      toast.success("工作区已创建");
      setNewName(""); setNewSlug(""); setShowCreate(false);
      await fetchWorkspaces();
      setActiveWorkspace(ws.workspace_id, ws.role);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "创建失败");
    }
    setCreating(false);
  };

  // Invite
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("editor");
  const [inviting, setInviting] = useState(false);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspaceId || !inviteEmail) return;
    setInviting(true);
    try {
      await workspaceApi.invite(activeWorkspaceId, inviteEmail, inviteRole);
      toast.success(`已邀请 ${inviteEmail}`);
      setInviteEmail("");
      fetchMembers(activeWorkspaceId);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "邀请失败");
    }
    setInviting(false);
  };

  const handleRoleChange = async (targetUserId: string, newRole: string) => {
    if (!activeWorkspaceId || !confirm(`将用户角色改为 ${newRole}？`)) return;
    try {
      await workspaceApi.updateMemberRole(activeWorkspaceId, targetUserId, newRole);
      toast.success("角色已更新");
      fetchMembers(activeWorkspaceId);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "更新失败");
    }
  };

  if (!hydrated) return <div className="min-h-screen"><NavHeader /><main className="p-8"><p className="text-gray-500">加载中...</p></main></div>;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <NavHeader />
      <main className="mx-auto max-w-4xl px-4 py-8">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">工作区设置</h1>

        {/* ---- Create form — always mounted, toggled via inline style ---- */}
        <div style={{ display: showCreate ? "block" : "none" }}>
          <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
            <form onSubmit={handleCreate}>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex-1 min-w-0">
                  <label className="mb-1 block text-xs text-gray-500">名称</label>
                  <input type="text" placeholder="产品团队" value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-white" />
                </div>
                <div className="w-full sm:w-40">
                  <label className="mb-1 block text-xs text-gray-500">Slug</label>
                  <input type="text" placeholder="product-team" value={newSlug}
                    onChange={(e) => setNewSlug(e.target.value.replace(/[^a-zA-Z0-9-]/g, "").toLowerCase())}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-white" />
                </div>
                <div className="flex gap-2">
                  <button type="submit" disabled={creating}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
                    {creating ? "创建中..." : "创建"}
                  </button>
                  <button type="button" onClick={() => { setShowCreate(false); setNewName(""); setNewSlug(""); }}
                    className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 whitespace-nowrap">
                    取消
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        {workspaces.length === 0 && !showCreate ? (
          <div className="rounded-xl bg-white p-8 text-center dark:bg-gray-900">
            <p className="text-gray-500 mb-4">你还没有加入任何工作区</p>
            <button type="button" onClick={() => setShowCreate(true)} className="rounded-lg bg-blue-600 px-4 py-2 text-white">创建第一个工作区</button>
          </div>
        ) : workspaces.length > 0 ? (
          <>
            <div className="mb-6 flex flex-wrap gap-2 items-center">
              {workspaces.map((w) => (
                <button key={w.workspace_id} type="button"
                  onClick={() => { setActiveWorkspace(w.workspace_id, w.role); setTab("general"); }}
                  className={`rounded-lg px-4 py-2 text-sm font-medium ${activeWorkspaceId === w.workspace_id ? "bg-blue-600 text-white" : "bg-white text-gray-700 dark:bg-gray-800 dark:text-gray-300"}`}>
                  {w.name} <span className="ml-1 text-xs opacity-70">({w.role})</span>
                </button>
              ))}
              <button type="button" id="btn-create-workspace"
                onClick={() => { setShowCreate(true); }}
                className="rounded-lg border border-dashed px-3 py-2 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600">
                + 新建
              </button>
              <span className="text-[10px] text-gray-400 ml-1">debug:showCreate={String(showCreate)}</span>
            </div>

            {activeWs && (
              <>
                <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit dark:bg-gray-800">
                  <TabBtn active={tab === "general"} onClick={() => setTab("general")}>概览</TabBtn>
                  {activeWs.role === "owner" || activeWs.role === "admin" ? (
                    <TabBtn active={tab === "members"} onClick={() => setTab("members")}>成员 ({members.length})</TabBtn>
                  ) : null}
                </div>

                {tab === "general" && (
                  <div className="rounded-xl bg-white p-6 dark:bg-gray-900">
                    <dl className="space-y-3 text-sm">
                      <Row label="名称" value={activeWs.name} />
                      <Row label="Slug" value={activeWs.slug} />
                      <Row label="我的角色" value={activeWs.role} />
                      <Row label="加入时间" value={activeWs.joined_at ? new Date(activeWs.joined_at).toLocaleString("zh-CN") : "-"} />
                    </dl>
                  </div>
                )}

                {tab === "members" && (
                  <div className="space-y-2">
                    {members.map((m) => (
                      <div key={m.user_id} className="flex items-center justify-between rounded-xl bg-white p-4 dark:bg-gray-900">
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">{m.name || m.email}</p>
                          <p className="text-xs text-gray-500">{m.email}</p>
                        </div>
                        <select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                          disabled={m.role === "owner" || (activeWs.role === "admin" && m.role === "admin")}
                          className="rounded-lg border px-3 py-1.5 text-sm dark:bg-gray-800 dark:text-white"
                        >
                          <option value="viewer">viewer</option>
                          <option value="editor">editor</option>
                          <option value="admin">admin</option>
                        </select>
                      </div>
                    ))}

                    <form onSubmit={handleInvite} className="mt-4 rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50">
                      <p className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">邀请成员</p>
                      <div className="flex gap-2">
                        <input type="email" placeholder="输入邮箱地址" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
                          className="flex-1 rounded-lg border px-3 py-2 text-sm dark:bg-gray-800 dark:text-white" />
                        <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}
                          className="rounded-lg border px-3 py-2 text-sm dark:bg-gray-800 dark:text-white">
                          <option value="viewer">viewer</option>
                          <option value="editor">editor</option>
                          <option value="admin">admin</option>
                        </select>
                        <button type="submit" disabled={inviting || !inviteEmail}
                          className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
                          {inviting ? "邀请中..." : "邀请"}
                        </button>
                      </div>
                    </form>
                  </div>
                )}
              </>
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}

function TabBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button onClick={onClick} className={`rounded-md px-4 py-1.5 text-sm font-medium ${active ? "bg-white text-gray-900 shadow dark:bg-gray-700 dark:text-white" : "text-gray-500"}`}>{children}</button>;
}

function Row({ label, value }: { label: string; value: string }) {
  return <div className="flex justify-between border-b border-gray-100 py-2 dark:border-gray-800"><span className="text-gray-500">{label}</span><span className="text-gray-900 dark:text-white">{value}</span></div>;
}

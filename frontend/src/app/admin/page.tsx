"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import Shell from "@/components/layout/Shell";
import PageHeader from "@/components/ui/PageHeader";
import Card from "@/components/ui/Card";
import { Play, RefreshCw, Plus, AlertCircle, CheckCircle2, Clock } from "lucide-react";

export default function AdminPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [newUser, setNewUser] = useState({ email: "", password: "", full_name: "", role: "viewer" });

  const { data: sources } = useQuery({
    queryKey: ["sources"],
    queryFn: async () => (await api().get("admin/ingestion/sources")).data,
  });

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["ingestion-status"],
    queryFn: async () => (await api().get("meta/ingestion-status")).data,
    refetchInterval: 5000,
  });

  const { data: users, refetch: refetchUsers } = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api().get("admin/users")).data,
  });

  const trigger = useMutation({
    mutationFn: (source: string) => api().post(`admin/ingestion/trigger/${source}`),
    onSuccess: () => {
      setTimeout(() => refetchStatus(), 1000);
    },
  });

  const createUser = useMutation({
    mutationFn: (u: typeof newUser) => api().post("admin/users", u),
    onSuccess: () => {
      setNewUser({ email: "", password: "", full_name: "", role: "viewer" });
      setShowAdd(false);
      refetchUsers();
    },
  });

  function statusFor(name: string) {
    return (status || []).find((s: any) => s.source === name);
  }

  return (
    <Shell>
      <div className="p-8 max-w-[1500px] mx-auto">
        <PageHeader title="Admin" subtitle="Ingestion control and user management" />

        {/* Ingestion */}
        <Card title="Ingestion Sources" className="mb-6">
          <div className="space-y-3">
            {(sources || []).map((s: any) => {
              const st = statusFor(s.name);
              return (
                <div key={s.name} className="flex items-center justify-between border border-gray-100 rounded-lg p-3">
                  <div>
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-gray-500">cron: <code>{s.schedule || "—"}</code></div>
                    {st && (
                      <div className="text-xs mt-1 flex items-center gap-2">
                        {st.status === "success" ? (
                          <span className="text-emerald-600 flex items-center gap-1"><CheckCircle2 size={12}/> success</span>
                        ) : st.status === "running" ? (
                          <span className="text-blue-600 flex items-center gap-1"><Clock size={12}/> running</span>
                        ) : (
                          <span className="text-red-600 flex items-center gap-1"><AlertCircle size={12}/> {st.status}</span>
                        )}
                        <span className="text-gray-500">last run: {st.last_run_at ? new Date(st.last_run_at).toLocaleString() : "never"}</span>
                        {st.rows_loaded != null && <span className="text-gray-500">· {st.rows_loaded.toLocaleString()} rows</span>}
                      </div>
                    )}
                    {st?.error_message && (
                      <div className="text-xs text-red-600 mt-1 truncate max-w-md">{st.error_message}</div>
                    )}
                  </div>
                  <button
                    onClick={() => trigger.mutate(s.name)}
                    disabled={trigger.isPending && trigger.variables === s.name}
                    className="flex items-center gap-2 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-sm disabled:opacity-50"
                  >
                    <Play size={14}/> Run now
                  </button>
                </div>
              );
            })}
          </div>
          <button
            onClick={() => refetchStatus()}
            className="mt-4 text-xs text-brand-600 flex items-center gap-1 hover:underline"
          >
            <RefreshCw size={12}/> Refresh status
          </button>
        </Card>

        {/* Users */}
        <Card title="Users">
          <div className="flex justify-end mb-4">
            <button
              onClick={() => setShowAdd(s => !s)}
              className="flex items-center gap-2 px-3 py-1.5 bg-brand-600 text-white rounded-lg text-sm"
            >
              <Plus size={14}/> Add user
            </button>
          </div>
          {showAdd && (
            <div className="mb-4 p-4 border border-gray-200 rounded-lg bg-gray-50 grid grid-cols-1 md:grid-cols-5 gap-3">
              <input
                placeholder="email"
                value={newUser.email}
                onChange={e => setNewUser({...newUser, email: e.target.value})}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
              />
              <input
                placeholder="password (min 8)"
                value={newUser.password}
                onChange={e => setNewUser({...newUser, password: e.target.value})}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
              />
              <input
                placeholder="full name"
                value={newUser.full_name}
                onChange={e => setNewUser({...newUser, full_name: e.target.value})}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
              />
              <select
                value={newUser.role}
                onChange={e => setNewUser({...newUser, role: e.target.value})}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm"
              >
                <option value="viewer">viewer</option>
                <option value="analyst">analyst</option>
                <option value="admin">admin</option>
              </select>
              <button
                onClick={() => createUser.mutate(newUser)}
                disabled={createUser.isPending || newUser.password.length < 8}
                className="bg-emerald-600 text-white rounded text-sm disabled:opacity-50"
              >
                {createUser.isPending ? "Saving…" : "Save"}
              </button>
              {createUser.isError && (
                <div className="md:col-span-5 text-sm text-red-600">
                  {(createUser.error as any)?.response?.data?.detail || "Create failed"}
                </div>
              )}
            </div>
          )}
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200">
              <tr className="text-left text-gray-500 text-xs uppercase tracking-wide">
                <th className="py-2 pr-4">ID</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 pr-4">Active</th>
                <th className="py-2 pr-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {(users || []).map((u: any) => (
                <tr key={u.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 text-gray-500">{u.id}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{u.email}</td>
                  <td className="py-2 pr-4">{u.full_name}</td>
                  <td className="py-2 pr-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      u.role === "admin" ? "bg-red-100 text-red-700"
                      : u.role === "analyst" ? "bg-blue-100 text-blue-700"
                      : "bg-gray-100 text-gray-700"
                    }`}>{u.role}</span>
                  </td>
                  <td className="py-2 pr-4">{u.is_active ? "✓" : "—"}</td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </Shell>
  );
}

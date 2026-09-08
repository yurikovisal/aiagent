"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Department { id: number; code: string; name: string }
interface Employee { id: number; full_name: string; role_title: string; department_id?: number | null; status: string }

interface EmployeeDetail {
  employee: Employee;
  attendance: { day: string; status: string; hours: number }[];
  attendance_rate_30d: number | null;
  kpis: { name: string; period: string; target: number; actual: number; unit: string }[];
  reports: { submitted_at: string; content: string }[];
  open_tasks: { id: number; title: string; status: string }[];
}

const ATTENDANCE_LABELS: Record<string, string> = { PRESENT: "На месте", ABSENT: "Отсутствовал", SICK: "Больничный", VACATION: "Отпуск" };

function EmployeeDetailPanel({ employeeId }: { employeeId: number }) {
  const [detail, setDetail] = useState<EmployeeDetail | null>(null);

  useEffect(() => {
    apiFetch<EmployeeDetail>(`/api/v1/employees/${employeeId}`).then(setDetail).catch(() => setDetail(null));
  }, [employeeId]);

  if (!detail) return <div className="p-3 text-xs text-base-muted">Загрузка...</div>;

  return (
    <div className="space-y-3 border-t border-base-border bg-base-bg/40 p-3 text-xs">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <p className="text-[10px] uppercase text-base-muted">Посещаемость (30 дн.)</p>
          <p className="mt-0.5 font-medium">{detail.attendance_rate_30d != null ? `${Math.round(detail.attendance_rate_30d * 100)}%` : "—"}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase text-base-muted">Открытых задач</p>
          <p className="mt-0.5 font-medium">{detail.open_tasks.length}</p>
        </div>
      </div>

      {detail.kpis.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] uppercase text-base-muted">KPI</p>
          <div className="space-y-1">
            {detail.kpis.map((k, i) => (
              <div key={i} className="flex items-center justify-between">
                <span>{k.name} ({k.period})</span>
                <span className={k.actual >= k.target ? "text-sev-low" : "text-sev-medium"}>{k.actual}{k.unit} / {k.target}{k.unit}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {detail.open_tasks.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] uppercase text-base-muted">Открытые задачи</p>
          <ul className="list-inside list-disc space-y-0.5 text-base-muted">
            {detail.open_tasks.map((t) => <li key={t.id}>{t.title}</li>)}
          </ul>
        </div>
      )}

      {detail.reports.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] uppercase text-base-muted">Последний отчёт</p>
          <p className="text-base-muted">{detail.reports[0].content}</p>
        </div>
      )}

      {detail.attendance.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] uppercase text-base-muted">Посещаемость (последние дни)</p>
          <div className="flex flex-wrap gap-1">
            {detail.attendance.slice(0, 14).map((a, i) => (
              <span key={i} title={`${a.day}: ${ATTENDANCE_LABELS[a.status] || a.status}`}
                className={`h-2 w-2 rounded-full ${a.status === "PRESENT" ? "bg-sev-low" : "bg-sev-medium"}`} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function EmployeesPage() {
  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [employees, setEmployees] = useState<Employee[] | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    apiFetch<Department[]>("/api/v1/departments").then(setDepartments).catch(() => setDepartments([]));
    apiFetch<Employee[]>("/api/v1/employees").then(setEmployees).catch(() => setEmployees([]));
  }, []);

  const byDept = (deptId: number) => (employees || []).filter((e) => e.department_id === deptId);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold tracking-tight">Employees</h1>
      {departments === null || employees === null ? (
        <p className="text-xs text-base-muted">Загрузка...</p>
      ) : departments.length === 0 ? (
        <Panel><EmptyState text="Подразделений нет." /></Panel>
      ) : (
        departments.map((dep) => (
          <Panel key={dep.id} title={dep.name} subtitle={`${byDept(dep.id).length} сотрудников`}>
            {byDept(dep.id).length === 0 ? <EmptyState text="Нет сотрудников." /> : (
              <div className="space-y-1">
                {byDept(dep.id).map((e) => (
                  <div key={e.id} className="rounded border border-base-border bg-base-panel2">
                    <button
                      onClick={() => setExpanded(expanded === e.id ? null : e.id)}
                      className="flex w-full items-center justify-between px-3 py-1.5 text-left text-xs"
                    >
                      <span>{e.full_name}</span>
                      <span className="text-base-muted">{e.role_title}</span>
                    </button>
                    {expanded === e.id && <EmployeeDetailPanel employeeId={e.id} />}
                  </div>
                ))}
              </div>
            )}
          </Panel>
        ))
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Panel, EmptyState } from "@/components/Panel";

interface Department { id: number; code: string; name: string }
interface Employee { id: number; full_name: string; role_title: string; department_id?: number | null; status: string }

export default function EmployeesPage() {
  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [employees, setEmployees] = useState<Employee[] | null>(null);

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
                  <div key={e.id} className="flex items-center justify-between rounded border border-base-border bg-base-panel2 px-3 py-1.5 text-xs">
                    <span>{e.full_name}</span>
                    <span className="text-base-muted">{e.role_title}</span>
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

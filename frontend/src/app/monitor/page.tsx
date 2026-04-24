"use client";

import { MonitorDashboard } from "@/components/monitor/MonitorDashboard";


export default function MonitorPage() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">盯盘区</h1>
        <p className="text-sm text-muted-foreground">
          单独查看后台盯盘状态、提醒规则、最近异动事件和手动扫描入口
        </p>
      </div>
      <MonitorDashboard />
    </div>
  );
}

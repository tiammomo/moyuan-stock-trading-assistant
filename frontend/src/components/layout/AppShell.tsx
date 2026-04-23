"use client";

import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { ToastContainer } from "@/components/ui/Toast";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background relative">
      {/* Background grid effect */}
      <div className="absolute inset-0 grid-bg opacity-30" />

      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden relative z-10">
        <Header />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>

      <ToastContainer />
    </div>
  );
}

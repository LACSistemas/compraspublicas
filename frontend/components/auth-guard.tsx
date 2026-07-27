"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface Props {
  children: React.ReactNode;
  requireOwner?: boolean;
}

export function AuthGuard({ children, requireOwner = false }: Props) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!user.is_active) {
      router.replace("/aguardando");
      return;
    }
    if (requireOwner && !user.is_owner) {
      router.replace("/");
    }
  }, [user, loading, requireOwner, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <span className="text-muted-foreground text-sm">Carregando...</span>
      </div>
    );
  }

  if (!user || !user.is_active) return null;
  if (requireOwner && !user.is_owner) return null;

  return <>{children}</>;
}

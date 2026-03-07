import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import type { UserRole } from "@/types/database";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: usuario } = await supabase
    .from("usuarios")
    .select("rol, nombre, email")
    .eq("id", user.id)
    .single();

  if (!usuario || usuario.rol === "pendiente") {
    redirect("/pendiente");
  }

  return (
    <div className="flex h-screen bg-unergy-deep-purple">
      <Sidebar
        user={{
          nombre: usuario.nombre || user.user_metadata?.full_name || "",
          email: usuario.email,
          rol: usuario.rol as UserRole,
        }}
      />
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}

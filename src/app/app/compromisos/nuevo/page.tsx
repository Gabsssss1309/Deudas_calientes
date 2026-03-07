import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { ExtractionForm } from "./extraction-form";

export default async function NuevoCompromisoPage() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Role guard: admin or editor only
  const { data: usuario } = await supabase
    .from("usuarios")
    .select("rol")
    .eq("id", user.id)
    .single();

  if (!usuario || !["admin", "editor"].includes(usuario.rol)) {
    redirect("/app/compromisos");
  }

  // Fetch deudas for dropdown
  const { data: deudas } = await supabase
    .from("deudas")
    .select("id, nombre, acreedor")
    .order("nombre");

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-unergy-cream mb-6">
        Extraer Compromisos desde PDF
      </h1>
      <ExtractionForm deudas={deudas ?? []} />
    </div>
  );
}

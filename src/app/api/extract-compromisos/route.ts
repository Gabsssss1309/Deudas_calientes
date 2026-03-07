import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import Groq from "groq-sdk";
import { execFileSync } from "child_process";
import { writeFileSync, unlinkSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import type { ExtractedCompromiso } from "@/types/database";

const SYSTEM_PROMPT = `Eres un extractor exhaustivo de obligaciones contractuales de project finance.

TU TAREA: Extraer TODAS las obligaciones, compromisos, covenants y condiciones que debe cumplir el Borrower, los Obligors, la SPV, el Sponsor, o cualquier parte del lado del deudor frente al Lender/acreedor.

BUSCA EXHAUSTIVAMENTE estos tipos de obligaciones:
- Reportes financieros (estados financieros, certificados de cumplimiento, DSCR, ratios)
- Reportes E&S (environmental & social reports, impact reporting, development impact, ESAP, ESMS)
- Seguros (polizas requeridas, renovaciones, certificados)
- Covenants financieros (DSCR minimo, ratios de endeudamiento, equity)
- Covenants positivos (mantener permisos, licencias, cumplir leyes, pagar impuestos)
- Covenants negativos (restricciones de deuda adicional, ventas de activos, cambio de control, distribuciones)
- Notificaciones (eventos de default, litigios, cambios materiales adversos)
- Condiciones precedentes (CPs para desembolso, CPs recurrentes)
- Cuentas y reservas (reserve accounts, debt service reserve, maintenance reserve)
- Governance (composicion de junta, key persons, cambios de accionistas)
- Permisos y licencias (mantener vigentes, renovar)
- Obligaciones tecnicas/operativas (O&M, performance ratios, mantenimiento)
- Anti-corrupcion, sanctions, KYC, AML
- Reportes de desarrollo e impacto (Development Impact Reporting)

CAMPOS (devuelve JSON array, cada objeto):
- clausula: numero exacto de clausula/sub-clausula (ej: "19.7(a)", "22.3", "Schedule 12")
- descripcion: descripcion DETALLADA del compromiso especifico (minimo 20 palabras). Incluye QUE debe entregarse/cumplirse, A QUIEN, y cualquier condicion.
- tipo_trigger: "periodico" | "evento" | "solicitud"
- plazo_dias: dias para cumplir (number o null)
- frecuencia: "mensual" | "trimestral" | "semestral" | "anual" | null
- responsable_sugerido: area interna encargada. Usa: Finanzas, Legal, E&S, Seguros, Operaciones, Compliance, Gerencia General
- notas: condiciones especiales, excepciones o referencias a schedules (string o null)

REGLAS:
- Si una clausula contiene multiples obligaciones distintas, crea UNA FILA POR CADA obligacion.
- NO omitas obligaciones porque parezcan menores. TODAS las obligaciones cuentan.
- Incluye obligaciones de Schedules/Anexos si aparecen en el texto.
- Devuelve SOLO el JSON array. Sin texto, sin markdown, sin backticks.`;

const CHUNK_SIZE = 12000; // chars per chunk (~3k tokens) - fits gemma2 15k TPM
const CHUNK_OVERLAP = 1500; // overlap to avoid cutting obligations
const INITIAL_DELAY_MS = 8000; // 8s delay between chunks for rate limits
const MAX_RETRIES = 3;

function splitIntoChunks(text: string): string[] {
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    const end = Math.min(start + CHUNK_SIZE, text.length);
    chunks.push(text.slice(start, end));
    start = end - CHUNK_OVERLAP;
    if (end === text.length) break;
  }
  return chunks;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function extractFromChunk(
  groq: Groq,
  chunk: string,
  chunkNum: number,
  totalChunks: number
): Promise<ExtractedCompromiso[]> {
  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const completion = await groq.chat.completions.create({
        model: "llama-3.3-70b-versatile",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          {
            role: "user",
            content: `Este es el fragmento ${chunkNum} de ${totalChunks} de un contrato de credito. Extrae TODAS las obligaciones que encuentres en este fragmento:\n\n${chunk}`,
          },
        ],
        temperature: 0.1,
        max_tokens: 3000,
      });

      const text = completion.choices[0]?.message?.content?.trim();
      if (!text) return [];

      let rawJson = text;
      if (rawJson.startsWith("```")) {
        rawJson = rawJson
          .replace(/^```(?:json)?\n?/, "")
          .replace(/\n?```$/, "");
      }

      try {
        const parsed = JSON.parse(rawJson);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        console.error(`Chunk ${chunkNum}: JSON parse failed, skipping`);
        return [];
      }
    } catch (err) {
      const isRateLimit =
        err instanceof Error &&
        (err.message.includes("rate_limit") ||
          err.message.includes("429") ||
          err.message.includes("413") ||
          err.message.includes("Too Many") ||
          err.message.includes("Request too large"));

      if (isRateLimit && attempt < MAX_RETRIES - 1) {
        // Wait based on retry delay from error, or exponential backoff
        const waitMs = 30000 + attempt * 30000; // 30s, 60s, 90s
        console.log(
          `Chunk ${chunkNum}: rate limited, waiting ${waitMs / 1000}s (attempt ${attempt + 1}/${MAX_RETRIES})`
        );
        await sleep(waitMs);
        continue;
      }
      throw err;
    }
  }
  return [];
}

function deduplicateCompromisos(
  items: ExtractedCompromiso[]
): ExtractedCompromiso[] {
  const seen = new Map<string, ExtractedCompromiso>();
  for (const item of items) {
    // Key by clausula + first 50 chars of description
    const key = `${item.clausula}::${(item.descripcion || "").slice(0, 50)}`;
    if (!seen.has(key)) {
      seen.set(key, item);
    }
  }
  return Array.from(seen.values());
}

export async function POST(request: Request) {
  try {
    // 1. Auth check
    const supabase = createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: "No autenticado" },
        { status: 401 }
      );
    }

    // 2. Role check
    const { data: usuario } = await supabase
      .from("usuarios")
      .select("rol")
      .eq("id", user.id)
      .single();
    if (!usuario || !["admin", "editor"].includes(usuario.rol)) {
      return NextResponse.json(
        { success: false, error: "No autorizado" },
        { status: 403 }
      );
    }

    // 3. Extract form data
    const formData = await request.formData();
    const file = formData.get("pdf") as File | null;
    const deudaId = formData.get("deuda_id") as string | null;
    if (!file || !deudaId) {
      return NextResponse.json(
        { success: false, error: "Archivo PDF y deuda son requeridos" },
        { status: 400 }
      );
    }

    // 4. Validate file
    if (file.size > 32 * 1024 * 1024) {
      return NextResponse.json(
        { success: false, error: "El archivo excede 32MB" },
        { status: 400 }
      );
    }
    if (file.type !== "application/pdf") {
      return NextResponse.json(
        { success: false, error: "Solo se aceptan archivos PDF" },
        { status: 400 }
      );
    }

    // 5. Upload PDF to Supabase Storage
    const adminClient = createAdminClient();
    const fileName = `${deudaId}/${Date.now()}_${file.name}`;
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const { error: uploadError } = await adminClient.storage
      .from("contratos")
      .upload(fileName, buffer, {
        contentType: "application/pdf",
        upsert: false,
      });

    if (uploadError) {
      return NextResponse.json(
        {
          success: false,
          error: `Error al subir archivo: ${uploadError.message}`,
        },
        { status: 500 }
      );
    }

    const { data: urlData } = adminClient.storage
      .from("contratos")
      .getPublicUrl(fileName);

    const { data: archivo, error: archivoError } = await adminClient
      .from("archivos")
      .insert({
        deuda_id: deudaId,
        tipo: "contrato",
        nombre_archivo: file.name,
        url_supabase: urlData.publicUrl,
      })
      .select("id")
      .single();

    if (archivoError) {
      return NextResponse.json(
        {
          success: false,
          error: `Error al registrar archivo: ${archivoError.message}`,
        },
        { status: 500 }
      );
    }

    // 6. Extract text from PDF via child_process
    const tmpPath = join(tmpdir(), `pdf-extract-${Date.now()}.pdf`);
    writeFileSync(tmpPath, buffer);

    let pdfText: string;
    try {
      const scriptPath = join(process.cwd(), "scripts", "extract-pdf-text.cjs");
      pdfText = execFileSync("node", [scriptPath, tmpPath], {
        maxBuffer: 50 * 1024 * 1024,
        timeout: 30000,
      }).toString();
    } finally {
      try {
        unlinkSync(tmpPath);
      } catch {
        /* ignore */
      }
    }

    if (!pdfText || pdfText.trim().length < 50) {
      return NextResponse.json(
        {
          success: false,
          error:
            "No se pudo extraer texto del PDF. Verifica que no sea un PDF escaneado.",
        },
        { status: 422 }
      );
    }

    // 7. Check mode: manual (return text + prompt) or auto (call Groq)
    const mode = formData.get("mode") as string | null;

    if (mode === "manual") {
      // Manual mode: return extracted text + prompt for Claude.ai
      return NextResponse.json({
        success: true,
        mode: "manual",
        pdfText,
        systemPrompt: SYSTEM_PROMPT,
        archivoId: archivo.id,
        stats: {
          chars: pdfText.length,
          estimatedTokens: Math.ceil(pdfText.length / 4),
        },
      });
    }

    // Auto mode: Call Groq in chunks
    const groqKey = process.env.GROQ_API_KEY;
    if (!groqKey) {
      return NextResponse.json(
        {
          success: false,
          error: "GROQ_API_KEY no configurada en el servidor",
        },
        { status: 500 }
      );
    }

    const groq = new Groq({ apiKey: groqKey });
    const chunks = splitIntoChunks(pdfText);
    const allCompromisos: ExtractedCompromiso[] = [];

    console.log(
      `Processing ${chunks.length} chunks (${pdfText.length} chars total)`
    );

    for (let i = 0; i < chunks.length; i++) {
      if (i > 0) {
        console.log(
          `Waiting ${INITIAL_DELAY_MS / 1000}s before chunk ${i + 1}...`
        );
        await sleep(INITIAL_DELAY_MS);
      }

      console.log(
        `Processing chunk ${i + 1}/${chunks.length} (${chunks[i].length} chars)`
      );
      const results = await extractFromChunk(groq, chunks[i], i + 1, chunks.length);
      allCompromisos.push(...results);
      console.log(`Chunk ${i + 1}: found ${results.length} compromisos`);
    }

    // 8. Deduplicate and return
    const deduplicated = deduplicateCompromisos(allCompromisos);

    if (deduplicated.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: "La IA no encontro compromisos en el documento",
        },
        { status: 422 }
      );
    }

    console.log(
      `Total: ${allCompromisos.length} raw → ${deduplicated.length} after dedup`
    );

    return NextResponse.json({
      success: true,
      data: deduplicated,
      archivoId: archivo.id,
    });
  } catch (err) {
    console.error("extract-compromisos API error:", err);

    let errorMsg = "Error inesperado al procesar el PDF";
    if (err instanceof Error) {
      errorMsg = err.message;
    }

    return NextResponse.json(
      { success: false, error: errorMsg },
      { status: 500 }
    );
  }
}

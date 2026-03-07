"use client";

import { useState, useTransition, useRef } from "react";
import { useRouter } from "next/navigation";
import type { ExtractedCompromiso } from "@/types/database";
import { saveCompromisos } from "./actions";
import { ReviewTable } from "./review-table";

type Step = "upload" | "processing" | "manual" | "review";

type DeudaOption = {
  id: string;
  nombre: string;
  acreedor: string;
};

interface Props {
  deudas: DeudaOption[];
}

export function ExtractionForm({ deudas }: Props) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("upload");
  const [selectedDeudaId, setSelectedDeudaId] = useState(
    deudas.length === 1 ? deudas[0].id : ""
  );
  const [file, setFile] = useState<File | null>(null);
  const [compromisos, setCompromisos] = useState<ExtractedCompromiso[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // Manual mode state
  const [fullPrompt, setFullPrompt] = useState("");
  const [pdfStats, setPdfStats] = useState({ chars: 0, estimatedTokens: 0 });
  const [jsonInput, setJsonInput] = useState("");
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleExtract = () => {
    if (!file || !selectedDeudaId) return;
    setError(null);
    setStep("processing");

    startTransition(async () => {
      try {
        const formData = new FormData();
        formData.append("pdf", file);
        formData.append("deuda_id", selectedDeudaId);
        formData.append("mode", "manual");

        const res = await fetch("/api/extract-compromisos", {
          method: "POST",
          body: formData,
        });
        const result = await res.json();

        if (result.success && result.mode === "manual") {
          // Build the full prompt for Claude.ai
          const prompt = `${result.systemPrompt}\n\n---\n\nA continuacion esta el texto completo del contrato de credito. Extrae TODAS las obligaciones:\n\n${result.pdfText}\n\n---\n\nDevuelve SOLO el JSON array con todas las obligaciones encontradas. Sin texto adicional, sin markdown, sin backticks.`;
          setFullPrompt(prompt);
          setPdfStats(result.stats);
          setStep("manual");
        } else if (result.success && result.data) {
          setCompromisos(result.data);
          setStep("review");
        } else {
          setError(result.error);
          setStep("upload");
        }
      } catch {
        setError("Error de conexion al procesar el PDF");
        setStep("upload");
      }
    });
  };

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(fullPrompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      // Fallback: select textarea content
      textareaRef.current?.select();
    }
  };

  const handleParseJson = () => {
    setError(null);
    const trimmed = jsonInput.trim();
    if (!trimmed) {
      setError("Pega el JSON de respuesta de Claude.ai");
      return;
    }

    // Clean markdown code blocks if present
    let cleaned = trimmed;
    if (cleaned.startsWith("```")) {
      cleaned = cleaned
        .replace(/^```(?:json)?\n?/, "")
        .replace(/\n?```$/, "");
    }

    try {
      const parsed = JSON.parse(cleaned);
      if (!Array.isArray(parsed)) {
        setError("El JSON debe ser un array. Verifica la respuesta de Claude.");
        return;
      }
      if (parsed.length === 0) {
        setError("El array esta vacio. Claude no encontro compromisos.");
        return;
      }
      setCompromisos(parsed);
      setStep("review");
    } catch {
      setError(
        "JSON invalido. Asegurate de copiar la respuesta completa de Claude.ai (solo el JSON array)."
      );
    }
  };

  const handleSave = () => {
    if (compromisos.length === 0) return;
    setError(null);

    startTransition(async () => {
      const result = await saveCompromisos(selectedDeudaId, compromisos);
      if (result.success) {
        router.push("/app/compromisos");
      } else {
        setError(result.error);
      }
    });
  };

  const handleReset = () => {
    setStep("upload");
    setFile(null);
    setCompromisos([]);
    setFullPrompt("");
    setJsonInput("");
    setError(null);
  };

  const selectedDeuda = deudas.find((d) => d.id === selectedDeudaId);

  // --- Step: Upload ---
  if (step === "upload") {
    return (
      <div className="card-unergy max-w-2xl">
        <h2 className="font-display text-lg font-semibold text-unergy-deep-purple mb-4">
          Subir contrato para extraer compromisos
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {/* Deuda selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Deuda
            </label>
            <select
              value={selectedDeudaId}
              onChange={(e) => setSelectedDeudaId(e.target.value)}
              className="w-full border border-gray-300 rounded-button px-3 py-2 text-sm bg-white focus:outline-none focus:border-unergy-purple"
            >
              <option value="">Seleccionar deuda...</option>
              {deudas.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nombre} — {d.acreedor}
                </option>
              ))}
            </select>
          </div>

          {/* File upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Archivo PDF del contrato
            </label>
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-button file:border-0 file:text-sm file:font-semibold file:bg-unergy-purple/10 file:text-unergy-purple hover:file:bg-unergy-purple/20 file:cursor-pointer"
            />
            <p className="mt-1 text-xs text-gray-400">
              Maximo 32MB. El texto se extraera y podras copiarlo para Claude.ai.
            </p>
          </div>

          {file && (
            <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
              <span className="font-medium">{file.name}</span>
              <span className="text-gray-400 ml-2">
                ({(file.size / 1024 / 1024).toFixed(1)} MB)
              </span>
            </div>
          )}

          <button
            onClick={handleExtract}
            disabled={!file || !selectedDeudaId || isPending}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? "Procesando..." : "Extraer Texto del Contrato"}
          </button>
        </div>
      </div>
    );
  }

  // --- Step: Processing ---
  if (step === "processing") {
    return (
      <div className="card-unergy max-w-2xl text-center py-12">
        <div className="inline-block w-12 h-12 border-4 border-unergy-purple/20 border-t-unergy-purple rounded-full animate-spin mb-6" />
        <h2 className="font-display text-lg font-semibold text-unergy-deep-purple mb-2">
          Extrayendo texto del PDF...
        </h2>
        <p className="text-sm text-gray-500">
          Subiendo el archivo y extrayendo el texto del contrato.
        </p>
        {selectedDeuda && (
          <p className="text-xs text-gray-400 mt-4">
            Deuda: {selectedDeuda.nombre} | Archivo: {file?.name}
          </p>
        )}
      </div>
    );
  }

  // --- Step: Manual (Claude.ai assisted) ---
  if (step === "manual") {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="card-unergy">
          <h2 className="font-display text-lg font-semibold text-unergy-deep-purple mb-2">
            Extraccion asistida con Claude.ai
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            El texto del contrato fue extraido exitosamente ({pdfStats.chars.toLocaleString()} caracteres, ~{pdfStats.estimatedTokens.toLocaleString()} tokens).
            Sigue estos 3 pasos:
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          {/* Step 1: Copy prompt */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-unergy-purple text-white text-xs font-bold">1</span>
              <h3 className="font-medium text-sm text-gray-800">
                Copia el prompt completo
              </h3>
            </div>
            <div className="relative">
              <textarea
                ref={textareaRef}
                readOnly
                value={fullPrompt}
                rows={4}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono text-gray-600 bg-gray-50 resize-none"
              />
              <button
                onClick={handleCopyPrompt}
                className={`absolute top-2 right-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  copied
                    ? "bg-green-100 text-green-700"
                    : "bg-unergy-purple text-white hover:bg-unergy-purple/90"
                }`}
              >
                {copied ? "Copiado!" : "Copiar todo"}
              </button>
            </div>
          </div>

          {/* Step 2: Go to Claude.ai */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-unergy-purple text-white text-xs font-bold">2</span>
              <h3 className="font-medium text-sm text-gray-800">
                Pegalo en Claude.ai y espera la respuesta
              </h3>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
              <p>
                Abre{" "}
                <a
                  href="https://claude.ai/new"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold underline hover:text-blue-600"
                >
                  claude.ai/new
                </a>
                {" "}en otra pestana, pega el prompt completo y envia el mensaje.
                Claude respondera con un JSON array de compromisos.
              </p>
            </div>
          </div>

          {/* Step 3: Paste JSON response */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-unergy-purple text-white text-xs font-bold">3</span>
              <h3 className="font-medium text-sm text-gray-800">
                Pega la respuesta JSON de Claude aqui
              </h3>
            </div>
            <textarea
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder='[{"clausula": "19.7(a)", "descripcion": "...", ...}, ...]'
              rows={8}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono text-gray-700 bg-white focus:outline-none focus:border-unergy-purple resize-y"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleParseJson}
              disabled={!jsonInput.trim()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Parsear y Revisar
            </button>
            <button onClick={handleReset} className="btn-secondary">
              Volver
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- Step: Review ---
  return (
    <div>
      <div className="card-unergy mb-4">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-display text-lg font-semibold text-unergy-deep-purple">
            Compromisos extraidos
          </h2>
          <span className="text-sm text-gray-500">
            {compromisos.length} compromiso(s) encontrado(s)
          </span>
        </div>
        <p className="text-xs text-gray-400 mb-4">
          Revisa y edita los compromisos antes de guardar. Puedes modificar
          cualquier celda, eliminar filas o agregar nuevas.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <ReviewTable compromisos={compromisos} onChange={setCompromisos} />
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={isPending || compromisos.length === 0}
          className="btn-primary disabled:opacity-50"
        >
          {isPending ? "Guardando..." : "Guardar Compromisos"}
        </button>
        <button
          onClick={handleReset}
          disabled={isPending}
          className="btn-secondary disabled:opacity-50"
        >
          Volver
        </button>
      </div>
    </div>
  );
}

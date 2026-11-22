"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Paginated, StudyDocument } from "@/lib/types";
import { Label } from "./ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";

/** Shared document dropdown (chat, flashcards, quiz). Only "ready" documents
 *  can be used — the others are still being processed. */
export function DocumentPicker({
  value,
  onChange,
  allowAll = false,
  label = "Document",
}: {
  value: string | null;
  onChange: (id: string | null) => void;
  allowAll?: boolean;
  label?: string;
}) {
  const [docs, setDocs] = useState<StudyDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Paginated<StudyDocument>>("/documents?page=1&page_size=100")
      .then((res) => setDocs(res.items))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, []);

  const ready = docs.filter((d) => d.status === "ready");

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Select
        value={value ?? "all"}
        onValueChange={(v) => onChange(v === "all" ? null : v)}
        disabled={loading}
      >
        <SelectTrigger>
          <SelectValue
            placeholder={loading ? "Loading…" : "Choose a document"}
          />
        </SelectTrigger>
        <SelectContent>
          {allowAll && <SelectItem value="all">All documents</SelectItem>}
          {ready.map((d) => (
            <SelectItem key={d.id} value={d.id}>
              {d.title}
              {d.page_count ? ` (${d.page_count} pages)` : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {!loading && ready.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No ready documents yet — upload a PDF first.
        </p>
      )}
    </div>
  );
}

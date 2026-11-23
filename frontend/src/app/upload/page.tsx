"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  FileText,
  FolderUp,
  Loader2,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import type { Paginated, StudyDocument, Summary } from "@/lib/types";
import { Protected } from "@/components/protected";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const STATUS_VARIANT: Record<
  StudyDocument["status"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  ready: "default",
  processing: "secondary",
  uploading: "secondary",
  failed: "destructive",
};

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadPage() {
  const [docs, setDocs] = useState<StudyDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState("");
  const [summaryDoc, setSummaryDoc] = useState<StudyDocument | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryStyle, setSummaryStyle] = useState("standard");
  const fileRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch<Paginated<StudyDocument>>(
        "/documents?page=1&page_size=100"
      );
      setDocs(res.items);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // webkitdirectory is not a React prop: set it directly on the folder
  // input after mount, so the picker lets the user choose a whole folder
  // (Chrome/Edge). Phones ignore it and fall back to picking files.
  useEffect(() => {
    folderRef.current?.setAttribute("webkitdirectory", "");
  }, []);
  useEffect(() => {
    if (!docs.some((d) => d.status === "uploading" || d.status === "processing"))
      return;
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [docs, load]);

  async function handleFiles(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (picked.length === 0) return;

    const pdfs = picked.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    const skipped = picked.length - pdfs.length;
    const tooBig = pdfs.filter((f) => f.size > 25 * 1024 * 1024);
    const toUpload = pdfs.filter((f) => f.size <= 25 * 1024 * 1024);
    if (skipped > 0) {
      toast.error(`${skipped} non-PDF file(s) skipped — only PDFs are supported`);
    }
    if (tooBig.length > 0) {
      toast.error(
        `${tooBig.length} file(s) skipped — larger than the 25 MB limit`
      );
    }
    if (toUpload.length === 0) return;

    setUploading(true);
    let done = 0;
    let failed = 0;
    try {
      for (const file of toUpload) {
        setUploadProgress(`Uploading ${done + 1} of ${toUpload.length}…`);
        try {
          const form = new FormData();
          form.append("file", file);
          await apiFetch<StudyDocument>("/documents/upload", {
            method: "POST",
            body: form,
          });
          done += 1;
        } catch (err) {
          failed += 1;
          toast.error(
            `"${file.name}": ${err instanceof ApiError ? err.message : "Upload failed"}`
          );
        }
      }
      if (done > 0) {
        toast.success(
          done === 1
            ? "Upload started — processing in the background"
            : `${done} PDFs uploaded — processing in the background`
        );
      }
      if (failed > 0 && done === 0) {
        toast.error("All uploads failed — please try again");
      }
      load();
    } finally {
      setUploading(false);
      setUploadProgress("");
    }
  }

  async function handleDelete(id: string) {
    try {
      await apiFetch(`/documents/${id}`, { method: "DELETE" });
      toast.success("Document deleted");
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Delete failed");
    }
  }

  async function openSummary(doc: StudyDocument, style?: string) {
    setSummaryDoc(doc);
    setSummary(null);
    setSummaryLoading(true);
    try {
      const res = style
        ? await apiFetch<Summary>(`/documents/${doc.id}/summary/regenerate`, {
            method: "POST",
            body: JSON.stringify({ style }),
          })
        : await apiFetch<Summary>(`/documents/${doc.id}/summary`);
      setSummary(res);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Summary is not ready yet"
      );
      if (!style) setSummaryDoc(null);
    } finally {
      setSummaryLoading(false);
    }
  }

  return (
    <Protected>
      <div className="container space-y-6 py-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Upload PDF</h1>
            <p className="text-muted-foreground">
              Upload lecture notes or textbook chapters — up to 25 MB each.
              Pick several files, or a whole folder of PDFs at once.
            </p>
            {uploading && uploadProgress && (
              <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {uploadProgress}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Upload files
            </Button>
            <Button
              variant="outline"
              onClick={() => folderRef.current?.click()}
              disabled={uploading}
            >
              <FolderUp className="h-4 w-4" />
              Upload folder
            </Button>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,application/pdf"
            multiple
            className="hidden"
            onChange={handleFiles}
          />
          <input
            ref={folderRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={handleFiles}
          />
        </div>

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : docs.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 font-medium">No documents yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Upload your first PDF to get summaries, flashcards and quizzes.
                You can pick several files, or a whole folder, at once.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <Button onClick={() => fileRef.current?.click()}>
                  <Upload className="h-4 w-4" />
                  Upload files
                </Button>
                <Button
                  variant="outline"
                  onClick={() => folderRef.current?.click()}
                >
                  <FolderUp className="h-4 w-4" />
                  Upload folder
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {docs.map((d) => (
              <Card key={d.id}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-lg">{d.title}</CardTitle>
                      <CardDescription>
                        {d.filename} · {formatSize(d.file_size_bytes)}
                        {d.page_count ? ` · ${d.page_count} pages` : ""}
                      </CardDescription>
                    </div>
                    <Badge variant={STATUS_VARIANT[d.status]}>{d.status}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {d.status === "failed" && d.error_message && (
                    <p className="flex items-start gap-2 text-sm text-destructive">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                      {d.error_message}
                    </p>
                  )}
                  {d.status === "processing" && (
                    <p className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Extracting text and building the index…
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={d.status !== "ready"}
                      onClick={() => openSummary(d)}
                    >
                      <Sparkles className="h-4 w-4" />
                      Summary
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(d.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Summary dialog */}
        <Dialog
          open={summaryDoc !== null}
          onOpenChange={(open) => !open && setSummaryDoc(null)}
        >
          <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Summary — {summaryDoc?.title}</DialogTitle>
              <DialogDescription>
                Generated from the document. Regenerate in a different style
                any time.
              </DialogDescription>
            </DialogHeader>
            {summaryLoading ? (
              <div className="space-y-3 py-4">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            ) : summary ? (
              <div className="space-y-5">
                <div className="flex items-center gap-2">
                  <Select value={summaryStyle} onValueChange={setSummaryStyle}>
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="short">Short</SelectItem>
                      <SelectItem value="standard">Standard</SelectItem>
                      <SelectItem value="detailed">Detailed</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => summaryDoc && openSummary(summaryDoc, summaryStyle)}
                  >
                    <RefreshCw className="h-4 w-4" />
                    Regenerate
                  </Button>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">
                  {summary.content}
                </p>
                {summary.key_points.length > 0 && (
                  <div>
                    <h4 className="font-semibold">Key points</h4>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                      {summary.key_points.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {summary.key_concepts.length > 0 && (
                  <div>
                    <h4 className="font-semibold">Key concepts</h4>
                    <dl className="mt-2 space-y-2 text-sm">
                      {summary.key_concepts.map((c, i) => (
                        <div key={i}>
                          <dt className="font-medium">{c.term}</dt>
                          {c.definition && (
                            <dd className="text-muted-foreground">
                              {c.definition}
                            </dd>
                          )}
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
                {summary.important_questions.length > 0 && (
                  <div>
                    <h4 className="font-semibold">Important questions</h4>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                      {summary.important_questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : null}
          </DialogContent>
        </Dialog>
      </div>
    </Protected>
  );
}

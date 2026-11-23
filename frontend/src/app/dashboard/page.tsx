"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  FileText,
  Flame,
  Layers,
  Loader2,
  Sparkles,
  Target,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  ActivityPoint,
  Paginated,
  ProgressStats,
  RecentQuizAttempt,
  RecentSummary,
  StudyDocument,
} from "@/lib/types";
import { cn } from "@/lib/utils";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const ACTIVITY_TYPES = ["reading", "chat", "flashcards", "quiz"] as const;

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function scoreBadgeClass(percentage: number) {
  if (percentage >= 70) return "bg-green-600 text-white hover:bg-green-600";
  if (percentage >= 40) return "bg-amber-500 text-white hover:bg-amber-500";
  return "bg-destructive text-destructive-foreground hover:bg-destructive";
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<ProgressStats | null>(null);
  const [activity, setActivity] = useState<ActivityPoint[]>([]);
  const [docs, setDocs] = useState<StudyDocument[]>([]);
  const [summaries, setSummaries] = useState<RecentSummary[]>([]);
  const [attempts, setAttempts] = useState<RecentQuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [logMinutes, setLogMinutes] = useState(30);
  const [logType, setLogType] = useState<string>("reading");
  const [logging, setLogging] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, a, d, sums, att] = await Promise.all([
        apiFetch<ProgressStats>("/progress/stats"),
        apiFetch<ActivityPoint[]>("/progress/activity?days=14"),
        apiFetch<Paginated<StudyDocument>>("/documents?page=1&page_size=5"),
        apiFetch<RecentSummary[]>("/summaries/recent?limit=5"),
        apiFetch<RecentQuizAttempt[]>("/quizzes/attempts/recent?limit=5"),
      ]);
      setStats(s);
      setActivity(a);
      setDocs(d.items);
      setSummaries(sums);
      setAttempts(att);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function logSession() {
    setLogging(true);
    try {
      await apiFetch("/progress/sessions", {
        method: "POST",
        body: JSON.stringify({
          activity_type: logType,
          duration_minutes: logMinutes,
        }),
      });
      toast.success("Session logged");
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not log session");
    } finally {
      setLogging(false);
    }
  }

  const maxMinutes = Math.max(...activity.map((a) => a.minutes), 1);
  const recentMinutes = activity.reduce((sum, a) => sum + a.minutes, 0);
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <Protected>
      <div className="container space-y-6 py-8">
        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold">
              {greeting()}
              {firstName ? `, ${firstName}` : ""}
            </h1>
            <p className="text-muted-foreground">
              {new Date().toLocaleDateString(undefined, {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
              {" · "}
              Here&apos;s where your studying stands.
            </p>
          </div>
          {stats && stats.streak_days > 0 && (
            <Badge variant="secondary" className="px-3 py-1 text-sm">
              <Flame className="mr-1 h-4 w-4 text-orange-500" />
              {stats.streak_days}-day streak — keep it going
            </Badge>
          )}
        </div>

        {/* Stats */}
        {loading ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28" />
            ))}
          </div>
        ) : (
          stats && (
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <StatCard
                icon={Flame}
                label="Study streak"
                value={`${stats.streak_days} days`}
                sub="consecutive days"
              />
              <StatCard
                icon={FileText}
                label="Documents"
                value={String(stats.total_documents)}
                sub="PDFs uploaded"
              />
              <StatCard
                icon={Layers}
                label="Flashcards known"
                value={`${stats.flashcards_known}/${stats.flashcards_total}`}
                sub="cards mastered"
              />
              <StatCard
                icon={Target}
                label="Quiz average"
                value={
                  stats.average_quiz_score !== null
                    ? `${stats.average_quiz_score.toFixed(0)}%`
                    : "—"
                }
                sub={`${stats.total_quizzes_taken} quizzes taken`}
              />
            </div>
          )
        )}

        {/* Recent summaries + quiz scores */}
        <div className="grid gap-4 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent summaries</CardTitle>
                  <CardDescription>
                    The latest AI summaries of your documents.
                  </CardDescription>
                </div>
                <Link href="/upload">
                  <Button variant="ghost" size="sm">
                    View all
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : summaries.length === 0 ? (
                <div className="py-6 text-center">
                  <Sparkles className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No summaries yet. Upload a PDF and its summary will appear
                    here.
                  </p>
                  <Link href="/upload">
                    <Button className="mt-4" size="sm">
                      Upload a PDF
                    </Button>
                  </Link>
                </div>
              ) : (
                <ul className="divide-y">
                  {summaries.map((s) => (
                    <li key={s.document_id} className="py-3 first:pt-0 last:pb-0">
                      <Link href="/upload" className="group block">
                        <p className="font-medium group-hover:underline">
                          {s.document_title}
                        </p>
                        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                          {s.content_preview}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {s.key_points_count} key points ·{" "}
                          {formatDate(s.updated_at)}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent quiz scores</CardTitle>
                  <CardDescription>Your latest attempts.</CardDescription>
                </div>
                <Link href="/quiz">
                  <Button variant="ghost" size="sm">
                    Take a quiz
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : attempts.length === 0 ? (
                <div className="py-6 text-center">
                  <Target className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No quizzes taken yet.
                  </p>
                  <Link href="/quiz">
                    <Button className="mt-4" size="sm">
                      Take your first quiz
                    </Button>
                  </Link>
                </div>
              ) : (
                <ul className="divide-y">
                  {attempts.map((a) => (
                    <li
                      key={a.id}
                      className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-medium">{a.quiz_title}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(a.completed_at)} · {a.score}/{a.total}{" "}
                          correct
                        </p>
                      </div>
                      <Badge className={cn(scoreBadgeClass(a.percentage))}>
                        {a.percentage}%
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Documents + activity */}
        <div className="grid gap-4 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Uploaded documents</CardTitle>
                  <CardDescription>Your latest uploads.</CardDescription>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Link href="/upload">
                    <Button size="sm">
                      <Upload className="h-4 w-4" />
                      Upload PDF
                    </Button>
                  </Link>
                  <Link href="/upload">
                    <Button variant="ghost" size="sm">
                      Manage all
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-3">
                  <Skeleton className="h-14 w-full" />
                  <Skeleton className="h-14 w-full" />
                </div>
              ) : docs.length === 0 ? (
                <div className="py-6 text-center">
                  <FileText className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 text-sm text-muted-foreground">
                    No documents yet.
                  </p>
                  <Link href="/upload">
                    <Button className="mt-4" size="sm">
                      Upload your first PDF
                    </Button>
                  </Link>
                </div>
              ) : (
                <ul className="divide-y">
                  {docs.map((d) => (
                    <li
                      key={d.id}
                      className="flex flex-col gap-3 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
                        <div className="min-w-0">
                          <p className="truncate font-medium">{d.title}</p>
                          <p className="text-xs text-muted-foreground">
                            {d.page_count ? `${d.page_count} pages · ` : ""}
                            {d.status}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Link href={`/chat?doc=${d.id}`}>
                          <Button variant="outline" size="sm">
                            Chat
                          </Button>
                        </Link>
                        <Link href={`/quiz?doc=${d.id}`}>
                          <Button variant="outline" size="sm">
                            <BookOpen className="h-4 w-4" />
                            Quiz
                          </Button>
                        </Link>
                        <Link href={`/flashcards?doc=${d.id}`}>
                          <Button variant="outline" size="sm">
                            <Layers className="h-4 w-4" />
                            Cards
                          </Button>
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4 lg:col-span-2">
            {/* Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Last 14 days</CardTitle>
                <CardDescription>
                  {recentMinutes} minutes studied · keep the streak alive.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {activity.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No study sessions yet. Log one below to start your streak.
                  </p>
                ) : (
                  <>
                    <div className="flex h-24 items-end gap-1">
                      {activity.map((a) => (
                        <div
                          key={a.date}
                          className="flex-1"
                          title={`${a.date}: ${a.minutes} min`}
                        >
                          <div
                            className="w-full rounded-t bg-primary"
                            style={{
                              height: `${Math.max((a.minutes / maxMinutes) * 100, 2)}%`,
                            }}
                          />
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 flex justify-between text-xs text-muted-foreground">
                      <span>{activity[0]?.date}</span>
                      <span>{activity[activity.length - 1]?.date}</span>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Log a session */}
            <Card>
              <CardHeader>
                <CardTitle>Log a session</CardTitle>
                <CardDescription>
                  Studied offline? Record it here.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Activity</Label>
                  <Select value={logType} onValueChange={setLogType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTIVITY_TYPES.map((t) => (
                        <SelectItem key={t} value={t}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="minutes">Minutes</Label>
                  <Input
                    id="minutes"
                    type="number"
                    min={1}
                    max={1440}
                    value={logMinutes}
                    onChange={(e) => setLogMinutes(Number(e.target.value))}
                  />
                </div>
                <Button onClick={logSession} disabled={logging} className="w-full">
                  {logging && <Loader2 className="h-4 w-4 animate-spin" />}
                  Log session
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Protected>
  );
}

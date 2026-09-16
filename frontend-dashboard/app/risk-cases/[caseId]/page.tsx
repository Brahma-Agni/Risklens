'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ArrowLeft, ShieldAlert } from 'lucide-react';
import { DashboardShell, PageHeading } from '@/components/dashboard-shell';
import { DataMode, RiskBadge, StatusBadge } from '@/components/risk-ui';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { api } from '@/lib/api';
import { demoCaseDetail } from '@/lib/demo-data';
import type { RiskCaseDetail } from '@/lib/types';

export default function RiskCaseDetailPage() {
  const params = useParams<{ caseId: string }>();
  const caseId = params?.caseId ?? demoCaseDetail.caseId;
  const [detail, setDetail] = useState<RiskCaseDetail>({
    ...demoCaseDetail,
    caseId,
  });
  const [live, setLive] = useState(false);
  const [comment, setComment] = useState('');
  const [feedback, setFeedback] = useState('');
  useEffect(() => {
    api
      .case(caseId)
      .then((data) => {
        setDetail(data);
        setLive(true);
      })
      .catch(() => {});
  }, [caseId]);
  const decide = async (decision: string) => {
    try {
      await api.submitDecision(
        caseId,
        decision,
        comment || `Decision ${decision.toLowerCase()} from RiskLens dashboard`,
      );
      setFeedback(`Decision submitted: ${decision.replaceAll('_', ' ')}`);
    } catch {
      setFeedback(
        'Live case unavailable; the decision was previewed but not written.',
      );
    }
  };
  const factors = [
    ['Transaction', detail.transactionRisk],
    ['Account', detail.accountRisk],
    ['Behavior', detail.behaviorRisk],
    ['Temporal', detail.temporalRisk],
    ['Structural', detail.structuralRisk],
    ['Similarity', detail.similarityRisk],
  ] as const;
  return (
    <DashboardShell title={`Case ${caseId}`} eyebrow="Support investigation">
      <div className="flex gap-3">
        <Button render={<Link href="/" />} variant="outline" size="sm">
          <ArrowLeft /> High-risk links
        </Button>
      </div>
      <PageHeading
        title="Review the fraud evidence"
        description={detail.aiSummary}
      />
      <DataMode
        live={live}
        message="This representative case demonstrates the support review flow until a live case is available."
      />
      <section className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldAlert className="size-5" /> Why the AI flagged it
                decomposition
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {factors.map(([label, value]) => {
                const pct = Math.round(Number(value) * 100);
                return (
                  <div key={label}>
                    <div className="mb-2 flex justify-between text-sm">
                      <span>{label}</span>
                      <span className="text-muted-foreground">{pct}</span>
                    </div>
                    <div className="h-4 border-2 border-black bg-white">
                      <div
                        className={`h-full ${pct >= 85 ? 'bg-[#ff6b6b]' : pct >= 65 ? 'bg-[#ffd93d]' : 'bg-[#93c5fd]'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Evidence signals</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {detail.signals.map((signal) => (
                <div
                  key={`${signal.type}-${signal.source}`}
                  className="border-2 border-black bg-[#fffdf5] p-4 shadow-[3px_3px_0_#000]"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-medium">
                        {signal.type.replaceAll('_', ' ')}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {signal.source}
                      </p>
                    </div>
                    <RiskBadge value={Number(signal.score)} />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    {signal.description}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Case summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <StatusBadge status={detail.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Severity</span>
                <StatusBadge status={detail.severity} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Ring risk</span>
                <RiskBadge value={Number(detail.ringRisk)} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <span>{Math.round(Number(detail.confidence) * 100)}%</span>
              </div>
              <div className="border-t-2 border-black pt-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">
                  Recommendation
                </p>
                <p className="mt-2 leading-6">{detail.recommendation}</p>
              </div>
            </CardContent>
          </Card>
          {detail.status !== 'RESOLVED' ? (
            <Card className="bg-[#c4b5fd]">
              <CardHeader>
                <CardTitle>Analyst decision</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add rationale or supporting context"
                />
                {feedback ? (
                  <p className="border-2 border-black bg-white p-3 text-xs font-bold">
                    {feedback}
                  </p>
                ) : null}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['CONFIRMED_ABUSE', 'Confirm fraud'],
                    ['FALSE_POSITIVE', 'False positive'],
                  ].map(([decision, label]) => (
                    <AlertDialog key={decision}>
                      <AlertDialogTrigger
                        render={
                          <Button
                            variant={
                              decision === 'CONFIRMED_ABUSE'
                                ? 'destructive'
                                : 'outline'
                            }
                          />
                        }
                      >
                        {label}
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            Submit {label.toLowerCase()}?
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            This records an auditable analyst decision on case{' '}
                            {caseId}.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => decide(decision)}>
                            Submit decision
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-[#86efac]">
              <CardHeader>
                <CardTitle>Action already recorded</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {detail.decisions.map((decision) => (
                  <div
                    key={decision.id}
                    className="border-2 border-black bg-white p-3"
                  >
                    <StatusBadge status={decision.decision} />
                    <p className="mt-2 font-bold">{decision.analyst}</p>
                    <p className="mt-1">
                      {decision.comment || 'No comment recorded'}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </section>
    </DashboardShell>
  );
}

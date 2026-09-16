'use client';

import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Link2, ShieldAlert, ShieldCheck } from 'lucide-react';
import {
  api,
  HIGH_RISK_THRESHOLD,
  money,
  REFRESH_INTERVAL_MS,
} from '@/lib/api';
import type { RiskCaseDetail, Transaction } from '@/lib/types';
import { DashboardShell, PageHeading } from '@/components/dashboard-shell';
import { DataMode, RiskBadge } from '@/components/risk-ui';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export function Overview() {
  const [cases, setCases] = useState<RiskCaseDetail[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [connected, setConnected] = useState(false);
  const [evidence, setEvidence] = useState<RiskCaseDetail | null>(null);
  const [selected, setSelected] = useState<RiskCaseDetail | null>(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [decisionError, setDecisionError] = useState('');

  const load = async () => {
    try {
      const caseSummaries = await api.highRiskLinkedCases(100);
      const bundles = await Promise.all(
        caseSummaries.map(async (item) =>
          Promise.all([
            api.case(item.caseId),
            api.transaction(item.transactionId),
          ]),
        ),
      );
      setCases(bundles.map(([detail]) => detail));
      setTransactions(bundles.map(([, transaction]) => transaction));
      setConnected(true);
    } catch {
      setConnected(false);
    }
  };

  useEffect(() => {
    const kickoff = setTimeout(() => void load(), 0);
    const timer = setInterval(load, REFRESH_INTERVAL_MS);
    return () => {
      clearTimeout(kickoff);
      clearInterval(timer);
    };
  }, []);

  const rows = useMemo(
    () =>
      [...cases].sort(
        (a, b) => Number(b.ringRisk) - Number(a.ringRisk),
      ),
    [cases],
  );
  const paymentById = useMemo(
    () => new Map(transactions.map((item) => [item.transactionId, item])),
    [transactions],
  );

  const decide = async (decision: 'CONFIRMED_ABUSE' | 'FALSE_POSITIVE') => {
    if (!selected) return;
    setSubmitting(true);
    setDecisionError('');
    try {
      await api.submitDecision(
        selected.caseId,
        decision,
        comment ||
          (decision === 'CONFIRMED_ABUSE'
            ? 'Fraud confirmed from linked transaction evidence.'
            : 'Reviewed by customer support and cleared as a false positive.'),
      );
      setCases((current) =>
        current.filter((item) => item.caseId !== selected.caseId),
      );
      setSelected(null);
      setComment('');
    } catch (error) {
      setDecisionError(
        error instanceof Error ? error.message : 'Unable to save this action.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DashboardShell
      title="Linked high-risk transactions"
      eyebrow="Fraud review"
    >
      <PageHeading
        title="Payments linked to likely fraud"
        description="Only unresolved, high-risk payments are shown. Each row combines evidence from transaction, account, behavior, time, graph, and known-case sources."
      />
      <DataMode
        live={connected}
        message="The backend is unavailable. No placeholder fraud records are shown."
      />
      <div className="flex flex-wrap gap-3">
        <span className="neo-label bg-[#ff6b6b]">
          {rows.length} high-risk links
        </span>
        <span className="neo-label bg-[#ffd93d]">
          Threshold {Math.round(HIGH_RISK_THRESHOLD * 100)}+
        </span>
        <span className="neo-label bg-[#86efac]">Auto-refresh enabled</span>
      </div>
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Case / transaction</TableHead>
                  <TableHead>Customer → receiver</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Evidence sources</TableHead>
                  <TableHead>Review</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((item) => {
                  const payment = paymentById.get(item.transactionId);
                  const sources = [
                    ...new Set(item.signals.map((signal) => signal.source)),
                  ];
                  return (
                    <TableRow key={item.caseId} className="bg-[#fff7cc]">
                      <TableCell>
                        <p className="font-mono text-xs font-black">
                          {item.caseId}
                        </p>
                        <p className="mt-1 font-mono text-[11px]">
                          {item.transactionId}
                        </p>
                      </TableCell>
                      <TableCell>
                        <p className="font-black">{item.accountId}</p>
                        <p className="text-xs">
                          → {payment?.receiverId ?? 'Linked beneficiary'}
                        </p>
                      </TableCell>
                      <TableCell className="font-black">
                        {payment
                          ? money(Number(payment.amount), payment.currency)
                          : '—'}
                      </TableCell>
                      <TableCell>
                        <div className="flex max-w-sm flex-wrap gap-1">
                          {sources.map((source) => (
                            <span
                              key={source}
                              className="inline-flex items-center gap-1 border-2 border-black bg-white px-2 py-1 text-[10px] font-black uppercase"
                            >
                              <Link2 className="size-3" />
                              {source}
                            </span>
                          ))}
                        </div>
                        <Button
                          className="mt-2"
                          onClick={() => setEvidence(item)}
                          size="sm"
                          variant="outline"
                        >
                          View evidence
                        </Button>
                      </TableCell>
                      <TableCell>
                        <Button
                          onClick={() => {
                            setSelected(item);
                            setComment('');
                            setDecisionError('');
                          }}
                          size="sm"
                        >
                          Inspect <ArrowRight />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          {connected && rows.length === 0 ? (
            <div className="grid min-h-56 place-items-center p-8 text-center">
              <div>
                <ShieldCheck className="mx-auto size-12" />
                <p className="mt-3 text-xl font-black">
                  No unresolved high-risk payments
                </p>
                <p className="mt-1 text-sm font-medium">
                  New linked fraud cases will appear here automatically.
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <Dialog
        open={evidence !== null}
        onOpenChange={(open) => {
          if (!open) setEvidence(null);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto border-2 border-black bg-[#fffdf5] shadow-[8px_8px_0_#000] sm:max-w-2xl">
          {evidence ? (
            <>
              <DialogHeader>
                <DialogTitle>Evidence details</DialogTitle>
                <DialogDescription>
                  {evidence.caseId} · {evidence.transactionId}
                </DialogDescription>
              </DialogHeader>
              <p className="text-sm font-medium leading-6">
                {evidence.aiSummary}
              </p>
              <div className="space-y-3 border-t-2 border-black pt-4">
                {evidence.signals.map((signal) => (
                  <div key={`${signal.source}-${signal.type}`}>
                    <p className="text-xs font-black uppercase">
                      {signal.source} · {signal.type.replaceAll('_', ' ')}
                    </p>
                    <p className="mt-1 text-sm leading-6">
                      {signal.description}
                    </p>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open && !submitting) setSelected(null);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto border-2 border-black bg-[#fffdf5] p-0 shadow-[8px_8px_0_#000] sm:max-w-3xl">
          {selected ? (
            <>
              <DialogHeader className="border-b-2 border-black bg-[#ff6b6b] p-5 pr-14">
                <DialogTitle className="flex items-center gap-2 text-2xl font-black">
                  <ShieldAlert className="size-6" /> Fraud investigation
                </DialogTitle>
                <DialogDescription className="font-bold text-black">
                  {selected.caseId} · {selected.transactionId}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-5 p-5">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="border-2 border-black bg-white p-3 shadow-[3px_3px_0_#000]">
                    <p className="text-[10px] font-black uppercase">Customer</p>
                    <p className="mt-1 font-black">{selected.accountId}</p>
                  </div>
                  <div className="border-2 border-black bg-white p-3 shadow-[3px_3px_0_#000]">
                    <p className="text-[10px] font-black uppercase">Amount</p>
                    <p className="mt-1 font-black">
                      {paymentById.get(selected.transactionId)
                        ? money(
                            Number(
                              paymentById.get(selected.transactionId)?.amount,
                            ),
                            paymentById.get(selected.transactionId)?.currency,
                          )
                        : '—'}
                    </p>
                  </div>
                  <div className="border-2 border-black bg-[#ffd93d] p-3 shadow-[3px_3px_0_#000]">
                    <p className="text-[10px] font-black uppercase">
                      Fraud risk
                    </p>
                    <div className="mt-1">
                      <RiskBadge value={Number(selected.ringRisk)} />
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-black uppercase">
                    What is happening
                  </h3>
                  <p className="mt-2 border-2 border-black bg-white p-4 text-sm font-medium leading-6">
                    {selected.aiSummary}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-black uppercase">
                    Current fraud signals
                  </h3>
                  <div className="mt-2 space-y-2">
                    {selected.signals.map((signal) => (
                      <div
                        key={`${signal.source}-${signal.type}`}
                        className="flex flex-col gap-2 border-2 border-black bg-white p-3 sm:flex-row sm:items-start sm:justify-between"
                      >
                        <div>
                          <p className="font-black">
                            {signal.type.replaceAll('_', ' ')}
                          </p>
                          <p className="mt-1 text-xs font-medium">
                            {signal.description}
                          </p>
                          <span className="mt-2 inline-block bg-black px-2 py-1 text-[10px] font-black text-white uppercase">
                            {signal.source}
                          </span>
                        </div>
                        <RiskBadge value={Number(signal.score)} />
                      </div>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="action-comment"
                    className="text-sm font-black uppercase"
                  >
                    Support note
                  </label>
                  <Textarea
                    id="action-comment"
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="Record why this was confirmed or cleared"
                  />
                </div>
                {decisionError ? (
                  <p className="border-2 border-black bg-[#ff6b6b] p-3 text-sm font-bold">
                    {decisionError}
                  </p>
                ) : null}
                <div className="grid gap-3 border-t-2 border-black pt-5 sm:grid-cols-2">
                  <Button
                    variant="destructive"
                    disabled={submitting}
                    onClick={() => void decide('CONFIRMED_ABUSE')}
                  >
                    Confirm fraud
                  </Button>
                  <Button
                    variant="outline"
                    disabled={submitting}
                    onClick={() => void decide('FALSE_POSITIVE')}
                  >
                    Mark false positive
                  </Button>
                </div>
                <p className="text-center text-xs font-bold text-muted-foreground">
                  Saving either action removes this case from the current list
                  and records it in Actions taken.
                </p>
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </DashboardShell>
  );
}

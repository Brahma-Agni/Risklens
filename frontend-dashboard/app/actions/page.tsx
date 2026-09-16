'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { CheckCheck, ExternalLink } from 'lucide-react';
import { api, REFRESH_INTERVAL_MS } from '@/lib/api';
import type { AnalystAction } from '@/lib/types';
import { DashboardShell, PageHeading } from '@/components/dashboard-shell';
import { DataMode, StatusBadge } from '@/components/risk-ui';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export default function ActionsPage() {
  const [actions, setActions] = useState<AnalystAction[]>([]);
  const [connected, setConnected] = useState(false);
  const load = async () => {
    try {
      setActions(await api.analystActions(200));
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

  return (
    <DashboardShell title="Actions taken" eyebrow="Audit history">
      <PageHeading
        title="Completed fraud decisions"
        description="An immutable staff-facing list of actions already recorded against risk cases in PostgreSQL."
      />
      <DataMode
        live={connected}
        message="The analyst-action API is unavailable. No placeholder actions are shown."
      />
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action time</TableHead>
                  <TableHead>Case / transaction</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Handled by</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Case</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {actions.map((action) => (
                  <TableRow key={action.id}>
                    <TableCell className="whitespace-nowrap text-xs font-bold">
                      {new Date(action.createdAt).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <p className="font-mono text-xs font-black">
                        {action.caseId}
                      </p>
                      <p className="font-mono text-[11px]">
                        {action.transactionId}
                      </p>
                    </TableCell>
                    <TableCell className="font-bold">
                      {action.accountId}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={action.decision} />
                    </TableCell>
                    <TableCell>{action.analyst}</TableCell>
                    <TableCell className="max-w-md text-sm">
                      {action.comment || 'No comment recorded'}
                    </TableCell>
                    <TableCell>
                      <Button
                        render={
                          <Link
                            href={`/risk-cases/${action.caseId}`}
                            aria-label={`Open ${action.caseId}`}
                          />
                        }
                        variant="outline"
                        size="icon"
                      >
                        <ExternalLink />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {connected && actions.length === 0 ? (
            <div className="grid min-h-56 place-items-center p-8 text-center">
              <div>
                <CheckCheck className="mx-auto size-12" />
                <p className="mt-3 text-xl font-black">No actions taken yet</p>
                <p className="mt-1 text-sm font-medium">
                  Submitted case decisions will appear here automatically.
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </DashboardShell>
  );
}

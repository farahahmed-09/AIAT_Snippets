"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  listMembers,
  removeMember,
  updateMemberRole,
  type Member,
} from "@/lib/api/projects";
import { initials } from "@/lib/initials";
import type { ProjectRole } from "@/lib/api/me";
import { InviteMemberDialog } from "./_invite-member-dialog";

const roleBadgeVariant: Record<
  ProjectRole,
  "default" | "secondary" | "outline"
> = {
  manager: "default",
  editor: "secondary",
  viewer: "outline",
};

type Props = {
  projectId: number;
  myUserId: string;
  myRole: ProjectRole;
  initialMembers: Member[];
};

export function MembersTab({
  projectId,
  myUserId,
  myRole,
  initialMembers,
}: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["members", projectId] as const;
  const { data: members = initialMembers } = useQuery({
    queryKey,
    queryFn: () => listMembers(projectId),
    initialData: initialMembers,
  });

  const isManager = myRole === "manager";

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: ProjectRole }) =>
      updateMemberRole(projectId, userId, role),
    onSuccess: () => {
      toast.success("Role updated");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeMember(projectId, userId),
    onSuccess: (_data, userId) => {
      toast.success(
        userId === myUserId ? "You left the project" : "Member removed",
      );
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {members.length} member{members.length === 1 ? "" : "s"}
        </p>
        {isManager ? <InviteMemberDialog projectId={projectId} /> : null}
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Member</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="hidden sm:table-cell">Joined</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.map((m) => {
              const display = m.full_name?.trim() || m.email || m.user_id;
              const isSelf = m.user_id === myUserId;
              const canEdit = isManager && !isSelf;
              return (
                <TableRow key={m.user_id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="size-8">
                        {m.avatar_url ? (
                          <AvatarImage src={m.avatar_url} alt={display} />
                        ) : null}
                        <AvatarFallback>
                          {initials(m.full_name, m.email)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex flex-col">
                        <span className="text-sm font-medium">{display}</span>
                        {m.email && m.email !== display ? (
                          <span className="text-xs text-muted-foreground">
                            {m.email}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {canEdit ? (
                      <Select
                        value={m.role}
                        onValueChange={(value) =>
                          roleMutation.mutate({
                            userId: m.user_id,
                            role: value as ProjectRole,
                          })
                        }
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="manager">manager</SelectItem>
                          <SelectItem value="editor">editor</SelectItem>
                          <SelectItem value="viewer">viewer</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <Badge variant={roleBadgeVariant[m.role]}>{m.role}</Badge>
                    )}
                  </TableCell>
                  <TableCell className="hidden text-sm text-muted-foreground sm:table-cell">
                    {new Date(m.joined_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {isSelf ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm("Leave this project?"))
                            removeMutation.mutate(m.user_id);
                        }}
                      >
                        Leave
                      </Button>
                    ) : isManager ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Remove ${display}?`))
                            removeMutation.mutate(m.user_id);
                        }}
                      >
                        Remove
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

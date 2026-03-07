import { useNavigate } from 'react-router-dom';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Order, OrderStatus } from '@/types';

const statusVariant: Record<OrderStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  completed: 'default',
  in_progress: 'secondary',
  pending: 'outline',
  failed: 'destructive',
};

const statusLabel: Record<OrderStatus, string> = {
  completed: 'Completed',
  in_progress: 'In Progress',
  pending: 'Pending',
  failed: 'Failed',
};

export function OrdersTable({ orders }: { orders: Order[] }) {
  const navigate = useNavigate();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Order ID</TableHead>
          <TableHead>Title</TableHead>
          <TableHead>Agent</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Actions</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {orders.map(order => (
          <TableRow
            key={order.id}
            className="cursor-pointer"
            onClick={() => navigate(`/dashboard/${order.id}`)}
          >
            <TableCell className="font-mono text-sm">{order.id}</TableCell>
            <TableCell className="font-medium">{order.title}</TableCell>
            <TableCell>{order.agentName}</TableCell>
            <TableCell>
              <Badge variant={statusVariant[order.status]}>{statusLabel[order.status]}</Badge>
            </TableCell>
            <TableCell>{order.actions.length}</TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {new Date(order.updatedAt).toLocaleString()}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

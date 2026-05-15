import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { HotProduct } from '../types';

const columns: ColumnsType<HotProduct> = [
  {
    title: '排名',
    key: 'rank',
    width: 60,
    render: (_, __, index) => {
      if (index === 0) return <Tag color="#ff4d4f">1</Tag>;
      if (index === 1) return <Tag color="#ff7a45">2</Tag>;
      if (index === 2) return <Tag color="#ffa940">3</Tag>;
      return index + 1;
    },
  },
  { title: '商品名称', dataIndex: 'title', key: 'title', ellipsis: true },
  {
    title: '价格', dataIndex: 'price', key: 'price', width: 100,
    render: (v: number) => <span style={{ color: '#ff4d4f' }}>¥{v}</span>,
  },
  {
    title: '热度', dataIndex: 'hotness', key: 'hotness', width: 90,
    render: (v: number | null) => (
      <Tag color={v && v > 100 ? 'red' : v && v > 10 ? 'orange' : 'default'}>
        {v ? v.toFixed(0) : '0'}
      </Tag>
    ),
    sorter: (a, b) => (a.hotness || 0) - (b.hotness || 0),
    defaultSortOrder: 'descend',
  },
  {
    title: '想要', dataIndex: 'want_count', key: 'want_count', width: 80,
    render: (v: number) => v.toLocaleString(),
    sorter: (a, b) => a.want_count - b.want_count,
  },
  {
    title: '发布', dataIndex: 'days_ago', key: 'days_ago', width: 90,
    render: (v: number | null) => {
      if (v === null || v === undefined) return '-';
      if (v <= 1) return <Tag color="green">今天</Tag>;
      if (v <= 3) return <Tag color="blue">{v}天前</Tag>;
      if (v <= 7) return <Tag color="cyan">{v}天前</Tag>;
      if (v <= 15) return <span>{v}天前</span>;
      if (v <= 30) return <span style={{ color: '#999' }}>{v}天前</span>;
      return <span style={{ color: '#ccc' }}>{v}天前</span>;
    },
    sorter: (a, b) => (a.days_ago || 999) - (b.days_ago || 999),
  },
  {
    title: '浏览', dataIndex: 'view_count', key: 'view_count', width: 70,
    render: (v: number) => v > 0 ? v.toLocaleString() : '-',
  },
  { title: '卖家', dataIndex: 'seller_name', key: 'seller_name', width: 100 },
];

export default function HotTable({ data }: { data: HotProduct[] }) {
  return (
    <Table
      columns={columns}
      dataSource={data}
      rowKey="id"
      pagination={false}
      size="middle"
    />
  );
}

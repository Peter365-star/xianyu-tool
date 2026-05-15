import { useEffect, useState, useCallback } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Tag, message, Typography, Tooltip, Space } from 'antd';
import { PlusOutlined, ReloadOutlined, DownloadOutlined, CopyOutlined, LinkOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import client from '../api/client';
import type { CrawlTask } from '../types';

const { Text } = Typography;

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  done: 'success',
  failed: 'error',
};

const statusLabels: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  done: '已完成',
  failed: '失败',
};

interface ProductData {
  title: string;
  price: number;
  seller_name: string;
  link: string;
}

export default function Tasks() {
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await client.get<CrawlTask[]>('/crawl/status');
      setTasks(res.data);
    } catch {
      // error handled by interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const triggerCrawl = async () => {
    const values = await form.validateFields();
    try {
      await client.post('/crawl/trigger', {
        keyword: values.keyword,
        duration_minutes: values.duration_minutes || null,
      });
      message.success('爬取任务已创建');
      setModalOpen(false);
      form.resetFields();
      fetchTasks();
    } catch {
      // error handled by interceptor
    }
  };

  const exportCSV = (task: CrawlTask) => {
    const data = (task.products_data || []) as ProductData[];
    if (data.length === 0) {
      message.warning('没有可导出的数据');
      return;
    }
    const header = '标题,卖家名,价格,链接\n';
    const csv = header + data.map((p) =>
      `"${(p.title || '').replace(/"/g, '""')}","${(p.seller_name || '').replace(/"/g, '""')}","${p.price}","${p.link || ''}"`
    ).join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `xianyu_${task.keyword}_${dayjs(task.created_at).format('YYYYMMDDHHmm')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success(`已导出 ${data.length} 条数据`);
  };

  const copyProduct = async (p: ProductData) => {
    const text = [
      `标题：${p.title}`,
      `价格：¥${p.price}`,
      p.seller_name ? `卖家：${p.seller_name}` : '',
      p.link ? `链接：${p.link}` : '',
    ].filter(Boolean).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      message.success('已复制到剪贴板');
    } catch {
      message.error('复制失败');
    }
  };

  const copyAllProducts = async (task: CrawlTask) => {
    const data = (task.products_data || []) as ProductData[];
    if (data.length === 0) return;
    const text = data.map((p) =>
      `【${p.title}】¥${p.price}${p.seller_name ? ' @' + p.seller_name : ''}`
    ).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      message.success(`已复制 ${data.length} 条商品信息`);
    } catch {
      message.error('复制失败');
    }
  };

  const columns: ColumnsType<CrawlTask> = [
    { title: '关键词', dataIndex: 'keyword', key: 'keyword' },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => <Tag color={statusColors[s] || 'default'}>{statusLabels[s] || s}</Tag>,
    },
    { title: '抓取数', dataIndex: 'items_found', key: 'items_found', width: 80 },
    {
      title: '时长(分)', dataIndex: 'duration_minutes', key: 'duration', width: 80,
      render: (v: number | null) => v ? `${v}分钟` : '-',
    },
    { title: '策略', dataIndex: 'level', key: 'level', width: 60, render: (v: string | null) => v || '-' },
    {
      title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => dayjs(v).format('MM-DD HH:mm:ss'),
    },
    {
      title: '操作', key: 'actions', width: 180,
      render: (_, task) => (
        task.status === 'done' && task.products_data?.length ? (
          <Space size="small">
            <Tooltip title="导出CSV">
              <Button size="small" icon={<DownloadOutlined />} onClick={() => exportCSV(task)} />
            </Tooltip>
            <Tooltip title="一键复刻全部">
              <Button size="small" icon={<CopyOutlined />} onClick={() => copyAllProducts(task)} />
            </Tooltip>
          </Space>
        ) : null
      ),
    },
  ];

  const expandedRowRender = (task: CrawlTask) => {
    const data = (task.products_data || []) as ProductData[];
    if (!data || data.length === 0) {
      return <Text type="secondary">暂无爬取结果</Text>;
    }
    return (
      <Table
        dataSource={data.map((p, i) => ({ ...p, key: i }))}
        columns={[
          { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: 300 },
          { title: '卖家名', dataIndex: 'seller_name', key: 'seller_name', width: 120,
            render: (v: string) => v || '-' },
          { title: '价格', dataIndex: 'price', key: 'price', width: 100,
            render: (v: number) => <Text style={{ color: '#ff4d4f' }}>¥{v}</Text> },
          { title: '链接', dataIndex: 'link', key: 'link', width: 100,
            render: (v: string) => v ? (
              <a href={v} target="_blank" rel="noreferrer"><LinkOutlined /> 打开</a>
            ) : '-' },
          {
            title: '复刻', key: 'clone', width: 70,
            render: (_, p: ProductData) => (
              <Tooltip title="复制商品信息">
                <Button size="small" icon={<CopyOutlined />} onClick={() => copyProduct(p)} />
              </Tooltip>
            ),
          },
        ]}
        pagination={false}
        size="small"
        scroll={{ y: 400 }}
      />
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>爬虫管理</h2>
        <div>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} style={{ marginRight: 8 }}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建任务</Button>
        </div>
      </div>

      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        expandable={{
          expandedRowRender,
          rowExpandable: (task) => task.status === 'done',
        }}
      />

      <Modal title="新建爬取任务" open={modalOpen} onOk={triggerCrawl} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="keyword" label="搜索关键词" rules={[{ required: true, message: '请输入关键词' }]}>
            <Input placeholder="如: iPhone 15" />
          </Form.Item>
          <Form.Item name="duration_minutes" label="爬取时长（分钟，不填则单次爬取）">
            <InputNumber min={1} max={120} style={{ width: '100%' }} placeholder="不填则单次爬取" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

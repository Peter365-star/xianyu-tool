import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Row, Col, Card, Statistic, Spin, Tag, Button, message } from 'antd';
import { FireOutlined, SearchOutlined, CheckCircleOutlined, CloseCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import client from '../api/client';
import type { CategoryList, CrawlTask, ProductSearchResult } from '../types';

export default function Dashboard() {
  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [hotCounts, setHotCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [crawling, setCrawling] = useState<Record<string, boolean>>({});
  const [crawlAllRunning, setCrawlAllRunning] = useState(false);
  const navigate = useNavigate();

  const fetchCounts = useCallback(async () => {
    if (!categories) return;
    const counts: Record<string, number> = {};
    await Promise.all(
      categories.xianyu.map(async (cat) => {
        try {
          const res = await client.get<ProductSearchResult>('/products/hot', {
            params: { category: cat.id, source: 'one_click', limit: 1 },
          });
          counts[cat.id] = res.data.total;
        } catch {
          counts[cat.id] = 0;
        }
      })
    );
    setHotCounts(counts);
  }, [categories]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [catRes, taskRes] = await Promise.all([
          client.get<CategoryList>('/categories'),
          client.get<CrawlTask[]>('/crawl/status'),
        ]);
        setCategories(catRes.data);
        setTasks(taskRes.data);

        const counts: Record<string, number> = {};
        await Promise.all(
          catRes.data.xianyu.map(async (cat) => {
            try {
              const res = await client.get<ProductSearchResult>('/products/hot', {
                params: { category: cat.id, source: 'one_click', limit: 1 },
              });
              counts[cat.id] = res.data.total;
            } catch {
              counts[cat.id] = 0;
            }
          })
        );
        setHotCounts(counts);
      } catch {
        // empty
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const waitForCrawlComplete = (catId: string): Promise<void> => {
    return new Promise((resolve) => {
      const poll = setInterval(async () => {
        try {
          const res = await client.get<CrawlTask[]>('/crawl/status');
          const running = res.data.filter(
            (t) => t.category === catId && (t.status === 'running' || t.status === 'pending')
          );
          if (running.length === 0) {
            clearInterval(poll);
            resolve();
          }
        } catch {
          clearInterval(poll);
          resolve();
        }
      }, 5000);
    });
  };

  const oneClickCrawl = async (catId: string, catName: string) => {
    setCrawling((prev) => ({ ...prev, [catId]: true }));
    try {
      await client.post('/crawl/trigger', {
        keyword: catName,
        category: catId,
        source: 'one_click',
      });
      await waitForCrawlComplete(catId);
      setCrawling((prev) => ({ ...prev, [catId]: false }));
      await fetchCounts();
      message.success(`"${catName}" 爬取完成`);
    } catch {
      setCrawling((prev) => ({ ...prev, [catId]: false }));
      message.error(`"${catName}" 爬取失败`);
    }
  };

  const crawlAll = async () => {
    if (!categories) return;
    setCrawlAllRunning(true);
    message.info('按顺序爬取所有分类，请稍候...');
    for (const cat of categories.xianyu) {
      setCrawling((prev) => ({ ...prev, [cat.id]: true }));
      try {
        await client.post('/crawl/trigger', {
          keyword: cat.name,
          category: cat.id,
          source: 'one_click',
        });
        await waitForCrawlComplete(cat.id);
      } catch {
        // continue to next
      }
      setCrawling((prev) => ({ ...prev, [cat.id]: false }));
    }
    setCrawlAllRunning(false);
    await fetchCounts();
    message.success('所有分类爬取完成！');
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  const runningTasks = tasks.filter((t) => t.status === 'running').length;
  const failedTasks = tasks.filter((t) => t.status === 'failed').length;
  const totalProducts = Object.values(hotCounts).reduce((a, b) => a + b, 0);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2>选品概览</h2>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          loading={crawlAllRunning}
          onClick={crawlAll}
          size="large"
        >
          全部一键爬取
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card><Statistic title="商品总数" value={totalProducts} prefix={<FireOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="爬取任务" value={tasks.length} prefix={<SearchOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="运行中" value={runningTasks} styles={{ value: { color: '#1677ff' } }} prefix={<CheckCircleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="失败" value={failedTasks} styles={{ value: { color: '#ff4d4f' } }} prefix={<CloseCircleOutlined />} /></Card>
        </Col>
      </Row>

      <h3>行业爆款概览</h3>
      <Row gutter={[16, 16]}>
        {categories?.xianyu.map((cat) => (
          <Col xs={12} sm={8} md={6} key={cat.id}>
            <Card
              hoverable
              onClick={() => navigate(`/hot/${cat.id}`)}
              actions={[
                <Button
                  type="link"
                  icon={<ThunderboltOutlined />}
                  loading={crawling[cat.id]}
                  onClick={(e) => {
                    e.stopPropagation();
                    oneClickCrawl(cat.id, cat.name);
                  }}
                >
                  一键爬取
                </Button>,
              ]}
            >
              <Statistic title={cat.name} value={hotCounts[cat.id] || 0} suffix="个商品" />
            </Card>
          </Col>
        ))}
      </Row>

      <h3 style={{ marginTop: 24 }}>自定义行业</h3>
      <div>
        {categories?.industries.map((ind) => (
          <Tag key={ind} style={{ marginBottom: 8, cursor: 'pointer' }} color="orange" onClick={() => navigate(`/hot?industry=${encodeURIComponent(ind)}`)}>
            {ind}
          </Tag>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Select, Spin, Empty, Typography } from 'antd';
import client from '../api/client';
import HotTable from '../components/HotTable';
import TrendChart from '../components/TrendChart';
import type { CategoryList, HotProduct, ProductSearchResult } from '../types';

const { Title } = Typography;

export default function HotRanking() {
  const { industry: paramIndustry } = useParams();
  const [searchParams] = useSearchParams();
  const queryIndustry = searchParams.get('industry') || undefined;
  const industry = paramIndustry || queryIndustry;

  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(industry);
  const [selectedIndustry, setSelectedIndustry] = useState<string | undefined>(
    industry && !/^[a-z]+$/.test(industry) ? industry : undefined
  );
  const [data, setData] = useState<HotProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeFilter, setTimeFilter] = useState<string | undefined>();

  useEffect(() => {
    client.get<CategoryList>('/categories').then((res) => setCategories(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    const fetchHot = async () => {
      setLoading(true);
      const params: Record<string, string> = { limit: '50' };
      if (selectedCategory) params.category = selectedCategory;
      if (selectedIndustry) params.industry = selectedIndustry;
      if (timeFilter) params.time_filter = timeFilter;

      try {
        const res = await client.get<ProductSearchResult>('/products/hot', { params });
        setData(res.data.items);
      } catch {
        setData([]);
      } finally {
        setLoading(false);
      }
    };
    fetchHot();
  }, [selectedCategory, selectedIndustry, timeFilter]);

  const allOptions = [
    ...(categories?.xianyu.map((c) => ({ value: c.id, label: `[类目] ${c.name}` })) || []),
    ...(categories?.industries.map((i) => ({ value: i, label: `[行业] ${i}` })) || []),
  ];

  const title = selectedCategory
    ? categories?.xianyu.find((c) => c.id === selectedCategory)?.name
    : selectedIndustry || '全部';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>{title} 爆款榜</Title>
        <div style={{ display: 'flex', gap: 12 }}>
          <Select
            style={{ width: 140 }}
            placeholder="发布时间"
            options={[
              { value: '7d', label: '7天内' },
              { value: '15d', label: '15天内' },
              { value: '30d', label: '30天内' },
            ]}
            value={timeFilter}
            onChange={setTimeFilter}
            allowClear
            onClear={() => setTimeFilter(undefined)}
          />
          <Select
            style={{ width: 200 }}
            placeholder="选择行业/类目"
            options={allOptions}
            value={selectedCategory || selectedIndustry}
            onChange={(v) => {
              if (categories?.xianyu.find((c) => c.id === v)) {
                setSelectedCategory(v);
                setSelectedIndustry(undefined);
              } else {
                setSelectedIndustry(v);
                setSelectedCategory(undefined);
              }
            }}
            allowClear
            onClear={() => { setSelectedCategory(undefined); setSelectedIndustry(undefined); }}
          />
        </div>
      </div>

      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />
      ) : data.length > 0 ? (
        <>
          <TrendChart data={data} />
          <HotTable data={data} />
        </>
      ) : (
        <Empty description="该行业暂无数据，请先触发爬取" />
      )}
    </div>
  );
}

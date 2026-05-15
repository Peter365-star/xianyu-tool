import { useState, useEffect } from 'react';
import { Input, Select, Row, Col, Spin, Empty, Pagination } from 'antd';
import ProductCard from '../components/ProductCard';
import client from '../api/client';
import type { CategoryList, ProductSearchResult } from '../types';

const { Search: AntSearch } = Input;

export default function Search() {
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState<string | undefined>();
  const [industry, setIndustry] = useState<string | undefined>();
  const [sort, setSort] = useState('hot_score');
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<CategoryList | null>(null);
  const [result, setResult] = useState<ProductSearchResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    client.get<CategoryList>('/categories').then((res) => setCategories(res.data)).catch(() => {});
  }, []);

  const doSearch = async (p = 1) => {
    setLoading(true);
    setPage(p);
    try {
      const res = await client.get<ProductSearchResult>('/products/search', {
        params: { keyword: keyword || undefined, category, industry, sort, page: p, page_size: 20 },
      });
      setResult(res.data);
    } catch {
      // error handled by interceptor
    } finally {
      setLoading(false);
    }
  };

  const categoryOptions = (categories?.xianyu || []).map((c) => ({ value: c.id, label: c.name }));
  const industryOptions = (categories?.industries || []).map((i) => ({ value: i, label: i }));

  return (
    <div>
      <h2>商品搜索</h2>
      <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <AntSearch
            placeholder="搜索关键词"
            allowClear
            enterButton
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={() => doSearch(1)}
          />
        </Col>
        <Col xs={12} sm={5}>
          <Select
            placeholder="闲鱼类目"
            allowClear
            style={{ width: '100%' }}
            options={categoryOptions}
            value={category}
            onChange={(v) => { setCategory(v); setIndustry(undefined); }}
          />
        </Col>
        <Col xs={12} sm={5}>
          <Select
            placeholder="自定义行业"
            allowClear
            style={{ width: '100%' }}
            options={industryOptions}
            value={industry}
            onChange={(v) => { setIndustry(v); setCategory(undefined); }}
          />
        </Col>
        <Col xs={12} sm={3}>
          <Select
            style={{ width: '100%' }}
            value={sort}
            onChange={setSort}
            options={[
              { value: 'hot_score', label: '爆款指数' },
              { value: 'price_asc', label: '价格从低到高' },
              { value: 'price_desc', label: '价格从高到低' },
              { value: 'newest', label: '最新发布' },
            ]}
          />
        </Col>
        <Col xs={12} sm={3}>
          <Select
            style={{ width: '100%' }}
            value={category || industry}
            onChange={(v) => {
              if (categories?.xianyu.find((c) => c.id === v)) {
                setCategory(v);
                setIndustry(undefined);
              } else {
                setIndustry(v);
                setCategory(undefined);
              }
            }}
            options={[...categoryOptions, ...industryOptions]}
            placeholder="筛选行业"
            allowClear
            onClear={() => { setCategory(undefined); setIndustry(undefined); }}
          />
        </Col>
      </Row>

      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />
      ) : result ? (
        result.items.length > 0 ? (
          <>
            <Row gutter={[16, 16]}>
              {result.items.map((item) => (
                <Col xs={24} sm={12} md={8} lg={6} key={item.id}>
                  <ProductCard product={item} />
                </Col>
              ))}
            </Row>
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination
                current={result.page}
                total={result.total}
                pageSize={result.page_size}
                onChange={doSearch}
                showTotal={(total) => `共 ${total} 件商品`}
              />
            </div>
          </>
        ) : (
          <Empty description="暂无匹配商品" />
        )
      ) : (
        <Empty description="输入关键词开始搜索" />
      )}
    </div>
  );
}

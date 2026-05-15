import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { HotProduct } from '../types';

export default function TrendChart({ data }: { data: HotProduct[] }) {
  const priceBuckets: Record<string, number> = {};
  data.forEach((p) => {
    const low = Math.floor(p.price / 50) * 50;
    const high = low + 49;
    const bucket = `${low}-${high}`;
    priceBuckets[bucket] = (priceBuckets[bucket] || 0) + 1;
  });

  const chartData = Object.entries(priceBuckets)
    .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
    .map(([range, count]) => ({
      range: `¥${range}`,
      count,
    }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="range" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="count" fill="#1677ff" name="商品数量" />
      </BarChart>
    </ResponsiveContainer>
  );
}

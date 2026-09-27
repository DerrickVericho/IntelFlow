import { expect, test } from 'vitest'
import type { Broker } from '../types/research'
import { investorBrokerView } from '../features/flow/investor'

const brokers: Broker[] = [
  { broker_code: 'AA', side: 'buyer', rank: 1, buy_idr: 150, sell_idr: 50, net_idr: 100, foreign_net_idr: -40 },
  { broker_code: 'BB', side: 'seller', rank: 1, buy_idr: 20, sell_idr: 100, net_idr: -80, foreign_net_idr: 30 },
  { broker_code: 'CC', side: 'buyer', rank: 2, buy_idr: 40, sell_idr: 10, net_idr: 30, foreign_net_idr: null },
  { broker_code: 'DD', side: 'seller', rank: 2, buy_idr: 10, sell_idr: 30, net_idr: -20, foreign_net_idr: 0 },
]

test('all investors keep provider ranks and original signed nets', () => {
  expect(investorBrokerView(brokers, 'all').pairs).toEqual([
    { rank: 1, buyer: { broker_code: 'AA', net_idr: 100 }, seller: { broker_code: 'BB', net_idr: -80 } },
    { rank: 2, buyer: { broker_code: 'CC', net_idr: 30 }, seller: { broker_code: 'DD', net_idr: -20 } },
  ])
})

test('foreign and local views rank by investor net, omit missing breakdowns and zero nets', () => {
  expect(investorBrokerView(brokers, 'foreign')).toEqual({
    covered: 3, total: 4,
    pairs: [{ rank: 1, buyer: { broker_code: 'BB', net_idr: 30 }, seller: { broker_code: 'AA', net_idr: -40 } }],
  })
  expect(investorBrokerView(brokers, 'local')).toEqual({
    covered: 3, total: 4,
    pairs: [
      { rank: 1, buyer: { broker_code: 'AA', net_idr: 140 }, seller: { broker_code: 'BB', net_idr: -110 } },
      { rank: 2, buyer: undefined, seller: { broker_code: 'DD', net_idr: -20 } },
    ],
  })
})

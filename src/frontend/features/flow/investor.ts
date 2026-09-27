import type { Broker } from '../../types/research'

export type InvestorFilter = 'all' | 'foreign' | 'local'

export interface RankedBroker {
  broker_code: string
  net_idr: number
}

export interface BrokerPair {
  rank: number
  buyer?: RankedBroker
  seller?: RankedBroker
}

export interface InvestorBrokerView {
  pairs: BrokerPair[]
  covered: number
  total: number
}

const MAX_RANKS = 10

export function investorBrokerView(brokers: Broker[], investor: InvestorFilter): InvestorBrokerView {
  if (investor === 'all') {
    const ranks = [...new Set(brokers.map(broker => broker.rank))].sort((a, b) => a - b)
    return {
      covered: brokers.length,
      total: brokers.length,
      pairs: ranks.map(rank => {
        const buyer = brokers.find(broker => broker.rank === rank && broker.side === 'buyer')
        const seller = brokers.find(broker => broker.rank === rank && broker.side === 'seller')
        return {
          rank,
          buyer: buyer ? { broker_code: buyer.broker_code, net_idr: buyer.net_idr } : undefined,
          seller: seller ? { broker_code: seller.broker_code, net_idr: seller.net_idr } : undefined,
        }
      }),
    }
  }

  const covered = brokers.filter(broker => typeof broker.foreign_net_idr === 'number' && Number.isFinite(broker.foreign_net_idr))
  const values = covered.map(broker => ({
    broker_code: broker.broker_code,
    net_idr: investor === 'foreign' ? broker.foreign_net_idr! : broker.net_idr - broker.foreign_net_idr!,
  }))
  const buyers = values.filter(broker => broker.net_idr > 0)
    .sort((a, b) => b.net_idr - a.net_idr || a.broker_code.localeCompare(b.broker_code))
    .slice(0, MAX_RANKS)
  const sellers = values.filter(broker => broker.net_idr < 0)
    .sort((a, b) => a.net_idr - b.net_idr || a.broker_code.localeCompare(b.broker_code))
    .slice(0, MAX_RANKS)

  return {
    covered: covered.length,
    total: brokers.length,
    pairs: Array.from({ length: Math.max(buyers.length, sellers.length) }, (_, index) => ({
      rank: index + 1,
      buyer: buyers[index],
      seller: sellers[index],
    })),
  }
}

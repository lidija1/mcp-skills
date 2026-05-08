import { useState } from 'react'
import {
  BriefcaseBusiness,
  Building2,
  Check,
  HeartPulse,
  Home,
  ShieldAlert,
  ShoppingCart,
  UserRound,
  UsersRound,
  Waves,
} from 'lucide-react'

const LOBS = [
  { id: 'auto', label: 'Personal Auto' },
  { id: 'cyber', label: 'Cyber' },
  { id: 'homeowner', label: 'Homeowner' },
]

const CUSTOMER_TYPES = {
  auto: [
    {
      id: 'young_driver',
      title: 'Young Driver',
      icon: UserRound,
      summary: 'Under 25 driver profile for age-based underwriting validation.',
      details: ['Age 19-24', 'Useful for youthful-driver rules', 'Can be combined with SR-22 or license risks'],
      risk: 'Elevated',
    },
    {
      id: 'teen_driver',
      title: 'Teen Driver',
      icon: UserRound,
      summary: 'First-time driver profile for high-risk age and limited history flows.',
      details: ['Age 16-18', 'Tests first-driver assumptions', 'Good for rating boundary checks'],
      risk: 'High',
    },
    {
      id: 'high_risk_driver',
      title: 'High Risk Driver',
      icon: ShieldAlert,
      summary: 'SR-22 and revoked-license profile intended to trigger underwriting review.',
      details: ['SR-22 required', 'Revoked license', 'Strong UW trigger coverage'],
      risk: 'Critical',
    },
    {
      id: 'triple_risk',
      title: 'Triple Risk',
      icon: ShieldAlert,
      summary: 'Combines SR-22, revoked license, and under-25 risk into one profile.',
      details: ['SR-22', 'Revoked license', 'Under 25'],
      risk: 'Critical',
    },
    {
      id: 'clean_standard',
      title: 'Clean Standard',
      icon: Check,
      summary: 'Middle-aged clean-record driver for expected straight-through processing.',
      details: ['Owned vehicle', 'Clean license', 'No existing damage'],
      risk: 'Low',
    },
    {
      id: 'senior_driver',
      title: 'Senior Driver',
      icon: UserRound,
      summary: 'Older driver with ordinary usage and clean record assumptions.',
      details: ['Age 65-80', 'Commute use', 'Clean record'],
      risk: 'Low',
    },
    {
      id: 'business_driver',
      title: 'Business Driver',
      icon: BriefcaseBusiness,
      summary: 'Business-use vehicle profile for employment and usage validation.',
      details: ['Business vehicle use', 'Employed driver', 'Moderate exposure'],
      risk: 'Medium',
    },
    {
      id: 'leased_luxury',
      title: 'Leased Luxury',
      icon: BriefcaseBusiness,
      summary: 'Leased BMW-style vehicle profile requiring loss payee information.',
      details: ['Leased ownership', 'Loss payee required', 'Higher-value vehicle'],
      risk: 'Medium',
    },
    {
      id: 'multiple_accidents',
      title: 'Multiple Accidents',
      icon: ShieldAlert,
      summary: 'Prior damage and claim history profile for loss-related validation.',
      details: ['Pre-existing damage', 'Prior claims', 'UW review likely'],
      risk: 'High',
    },
  ],
  cyber: [
    {
      id: 'small_office',
      title: 'Small Office',
      icon: Building2,
      summary: 'Low-risk professional office with reasonable cyber hygiene.',
      details: ['Small employee count', 'Good controls', 'Low online exposure'],
      risk: 'Low',
    },
    {
      id: 'high_risk_startup',
      title: 'High Risk Startup',
      icon: ShieldAlert,
      summary: 'Technology startup with weak controls and prior incident history.',
      details: ['High online sales', 'Past breach', 'Limited training'],
      risk: 'High',
    },
    {
      id: 'established_retail',
      title: 'Established Retail',
      icon: ShoppingCart,
      summary: 'Retail business with moderate online activity and common cyber exposure.',
      details: ['Brick-and-mortar base', 'Some e-commerce', 'Moderate controls'],
      risk: 'Medium',
    },
    {
      id: 'healthcare_provider',
      title: 'Healthcare Provider',
      icon: HeartPulse,
      summary: 'Healthcare organization handling sensitive regulated data.',
      details: ['PHI exposure', 'Regulatory pressure', 'Medium-to-high control expectations'],
      risk: 'Medium',
    },
    {
      id: 'e_commerce',
      title: 'E-Commerce',
      icon: ShoppingCart,
      summary: 'Online-sales-heavy company for revenue and transaction exposure testing.',
      details: ['High online revenue', 'Payment flow exposure', 'Tech-dependent operations'],
      risk: 'Medium',
    },
    {
      id: 'financial_services',
      title: 'Financial Services',
      icon: BriefcaseBusiness,
      summary: 'Financial firm profile with stronger compliance and control posture.',
      details: ['Regulated business', 'Sensitive records', 'Stronger cyber controls'],
      risk: 'Medium',
    },
    {
      id: 'no_training_no_regs',
      title: 'No Training / No Regs',
      icon: ShieldAlert,
      summary: 'Poor cyber posture profile intended to find referral and control gaps.',
      details: ['No security training', 'Past incidents', 'UW referral likely'],
      risk: 'Critical',
    },
  ],
  homeowner: [
    {
      id: 'standard_homeowner',
      title: 'Standard Homeowner',
      icon: Home,
      summary: 'Average owner-occupied home with clean history and standard construction.',
      details: ['Frame construction', 'Clean history', 'Average replacement cost'],
      risk: 'Low',
    },
    {
      id: 'high_value_home',
      title: 'High Value Home',
      icon: Home,
      summary: 'Luxury property profile for large replacement cost and premium coverage flows.',
      details: ['Replacement cost over $800k', 'Premium coverage', 'Higher liability limits'],
      risk: 'Medium',
    },
    {
      id: 'risky_property',
      title: 'Risky Property',
      icon: ShieldAlert,
      summary: 'Prior losses, old construction, or renovation exposure for UW validation.',
      details: ['Prior loss history', 'Older construction', 'Renovation risk'],
      risk: 'High',
    },
    {
      id: 'new_construction',
      title: 'New Construction',
      icon: Check,
      summary: 'Recently built home with modern materials and lower expected risk.',
      details: ['Built 2018-2024', 'Modern construction', 'Clean profile'],
      risk: 'Low',
    },
    {
      id: 'risk_flagged',
      title: 'Risk Flagged',
      icon: ShieldAlert,
      summary: 'Multiple homeowner risk flags designed to trigger underwriting referral.',
      details: ['Refused coverage', 'Declined or non-renewed', 'Recent losses'],
      risk: 'Critical',
    },
    {
      id: 'coastal_exposure',
      title: 'Coastal Exposure',
      icon: Waves,
      summary: 'Windstorm-focused property profile with roof and construction sensitivity.',
      details: ['Windstorm deductible focus', 'Masonry or superior construction', 'Tile or metal roof'],
      risk: 'Medium',
    },
    {
      id: 'investment_property',
      title: 'Investment Property',
      icon: Building2,
      summary: 'Rented residence profile for occupancy, animal, and coverage validations.',
      details: ['Rented residence', 'Potential animal exposure', 'Standard coverage'],
      risk: 'Medium',
    },
  ],
}

const RISK_TONE = {
  Low: 'green',
  Medium: 'blue',
  Elevated: 'purple',
  High: 'orange',
  Critical: 'red',
}

export default function CustomersPanel() {
  const [lob, setLob] = useState('auto')
  const selectedTypes = CUSTOMER_TYPES[lob]

  return (
    <div className="panel-stack customers-panel animate-fade-in">
      <section className="page-heading">
        <h1>Customer Types</h1>
        <p>Browse persona archetypes used by Policy Flow generation and underwriting validation.</p>
      </section>

      <div className="lob-selector">
        <span>Line of Business:</span>
        {LOBS.map(item => (
          <button
            key={item.id}
            type="button"
            className={`lob-pill ${lob === item.id ? 'active' : ''}`}
            onClick={() => setLob(item.id)}
          >
            {lob === item.id && <Check size={17} />}
            {item.label}
          </button>
        ))}
      </div>

      <section className="customer-summary-card">
        <div className="card-icon blue">
          <UsersRound size={28} />
        </div>
        <div>
          <h2>{LOBS.find(item => item.id === lob)?.label} Archetypes</h2>
          <p>
            These profiles are prompt shortcuts for realistic test data. Use their names or descriptions in
            Quick Policy Test, Build Customer Profile, or custom UW edge cases.
          </p>
        </div>
      </section>

      <div className="customer-type-grid">
        {selectedTypes.map(type => (
          <CustomerTypeCard key={type.id} type={type} />
        ))}
      </div>
    </div>
  )
}

function CustomerTypeCard({ type }) {
  const Icon = type.icon
  const tone = RISK_TONE[type.risk] || 'blue'

  return (
    <article className="customer-type-card">
      <div className="customer-card-header">
        <div className={`customer-type-icon ${tone}`}>
          <Icon size={23} />
        </div>
        <span className={`risk-chip ${tone}`}>{type.risk}</span>
      </div>

      <h2>{type.title}</h2>
      <p>{type.summary}</p>

      <ul>
        {type.details.map(detail => (
          <li key={detail}>
            <Check size={15} />
            <span>{detail}</span>
          </li>
        ))}
      </ul>

      <code>{type.id}</code>
    </article>
  )
}

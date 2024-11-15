import React
import {useState
        import useEffect} from 'react'
import {LineChart
        import BarChart
        import Area
        import Bar
        import XAxis
        import YAxis
        import CartesianGrid
        import Tooltip
        import Legend
        import ResponsiveContainer} from 'recharts'
import {AlertTriangle
        import CheckCircle
        import XCircle
        import Clock
        import Server
        import Database
        import Shield
        import DollarSign} from 'lucide-react'
import {Alert
        import AlertDescription
        import AlertTitle} from '@/components/ui/alert'

const SREDashboard = () = > {
    const[activeTab, setActiveTab] = useState('overview')
    const[timeRange, setTimeRange] = useState('1h')

    const MetricCard = ({title, value, status, icon: Icon}) = > (
        < div className={`p-4 rounded-lg border ${
            status == = 'healthy' ? 'bg-green-50 border-green-200':
            status === 'warning' ? 'bg-yellow-50 border-yellow-200':
            'bg-red-50 border-red-200'
        }`} >
        < div className="flex items-center justify-between" >
        < div className="flex items-center space-x-2" >
        < Icon className={`w-5 h-5 ${
            status == = 'healthy' ? 'text-green-500':
            status === 'warning' ? 'text-yellow-500':
            'text-red-500'
        }`} / >
        < h3 className="font-medium text-gray-900" > {title} < /h3 >
        < / div >
        < span className="text-lg font-semibold" > {value} < /span >
        < / div >
        < / div >
    )

    const TimeRangeSelector = () = > (
        < div className="flex space-x-2 mb-4" >
        {['1h', '6h', '24h', '7d'].map((range)= > (
            < button
            key={range}
            onClick={()= > setTimeRange(range)}
            className={`px-3 py-1 rounded ${
                timeRange === range ? 'bg-blue-500 text-white': 'bg-gray-100'
            }`}
            >
            {range}
            < /button >
        ))}
        < /div >
    )

    const Overview = () = > (
        < div className="space-y-4" >
        < div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" >
        < MetricCard
        title="Cluster Health"
        value="98%"
        status="healthy"
        icon={Server}
        / >
        < MetricCard
        title="Error Rate"
        value="0.5%"
        status="healthy"
        icon={AlertTriangle}
        / >
        < MetricCard
        title="Response Time"
        value="250ms"
        status="warning"
        icon={Clock}
        / >
        < MetricCard
        title="Cost Trend"
        value="+2.3%"
        status="warning"
        icon={DollarSign}
        / >
        < /div >

        < div className="h-96 bg-white rounded-lg p-4 border" >
        < h3 className="text-lg font-medium mb-4" > System Performance < /h3 >
        < ResponsiveContainer width="100%" height="100%" >
        < LineChart
        data={[
            {time: '00:00', cpu: 45, memory: 62, network: 30},
            {time: '04:00', cpu: 55, memory: 65, network: 35},
            {time: '08:00', cpu: 75, memory: 78, network: 45},
            {time: '12:00', cpu: 85, memory: 82, network: 55},
            {time: '16:00', cpu: 70, memory: 75, network: 40},
            {time: '20:00', cpu: 60, memory: 68, network: 35},
        ]}
        >
        <CartesianGrid strokeDasharray="3 3" / >
        < XAxis dataKey="time" / >
        < YAxis / >
        < Tooltip / >
        < Legend / >
        < Line type="monotone" dataKey="cpu" stroke="#3b82f6" name="CPU %" / >
        < Line type="monotone" dataKey="memory" stroke="#10b981" name="Memory %" / >
        < Line type="monotone" dataKey="network" stroke="#6366f1" name="Network Load %" / >
        < /LineChart >
        < / ResponsiveContainer >
        < / div >
        < / div >
    )

    const AlertsList = () = > (
        < div className="space-y-4" >
        < Alert variant="destructive" >
        < AlertTriangle className="h-4 w-4" / >
        < AlertTitle > High Memory Usage < /AlertTitle >
        < AlertDescription >
        Pod memory usage exceeds 85 % in us-central1-a/cluster-1
        < /AlertDescription >
        < / Alert >
        < Alert variant="warning" >
        < AlertTriangle className="h-4 w-4" / >
        < AlertTitle > Increased Error Rate < /AlertTitle >
        < AlertDescription >
        5xx error rate increased to 0.5 % in the last 15 minutes
        < /AlertDescription >
        < / Alert >
        < / div >
    )

    return (
        < div className="p-6 max-w-7xl mx-auto" >
        < div className="mb-6 flex justify-between items-center" >
        < h1 className="text-2xl font-bold text-gray-900" > SRE Dashboard < /h1 >
        < TimeRangeSelector / >
        < /div >

        < div className="mb-6" >
        < nav className="flex space-x-4" >
        {['overview', 'kubernetes', 'errors', 'performance', 'costs', 'security'].map((tab)=> (
            < button
            key={tab}
            onClick={() = > setActiveTab(tab)}
            className={`px-3 py-2 rounded-md ${
                activeTab === tab
                ? 'bg-blue-500 text-white': 'text-gray-600 hover:bg-gray-100'
            }`}
            >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            < /button >
        ))}
        < /nav >
        < / div >

        < div className="space-y-6" >
        {activeTab === 'overview' & & < Overview / >}
        {/* Add other tab contents as needed * /}

        < div className="mt-6" >
        < h2 className="text-lg font-medium mb-4" > Recent Alerts < /h2 >
        < AlertsList / >
        < /div >
        < / div >
        < / div >
    )
};

export default SREDashboard

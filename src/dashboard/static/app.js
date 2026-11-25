document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Logic ---
    const navItems = document.querySelectorAll('.nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            // Remove active class from all
            navItems.forEach(nav => nav.classList.remove('active'));
            tabPanes.forEach(tab => tab.classList.remove('active'));
            
            // Add active class to clicked
            item.classList.add('active');
            const targetId = item.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // --- Data Fetching & Rendering ---
    
    // Status
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.getElementById('data-source-status');
            if (data.source === 'live') {
                statusDot.classList.add('connected');
                statusText.textContent = 'Live (Spark/Iceberg)';
            } else {
                statusText.textContent = 'Simulated Data';
            }
        })
        .catch(err => console.error("Status fetch error", err));

    // Metrics
    fetch('/api/metrics')
        .then(res => res.json())
        .then(data => {
            document.getElementById('metric-revenue').textContent = `₹${data.total_revenue.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            document.getElementById('metric-orders').textContent = data.total_orders.toLocaleString('en-IN');
            document.getElementById('metric-tax').textContent = `₹${data.total_tax.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        });

    // Revenue Chart
    fetch('/api/revenue')
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById('revenueChart').getContext('2d');
            
            // Process data for Chart.js
            const dates = [...new Set(data.map(item => item.sales_date))].sort();
            
            const shopifyData = dates.map(d => {
                const record = data.find(item => item.sales_date === d && item.channel === 'shopify');
                return record ? record.gross_revenue : 0;
            });
            
            const posData = dates.map(d => {
                const record = data.find(item => item.sales_date === d && item.channel === 'pos');
                return record ? record.gross_revenue : 0;
            });
            
            const distributorData = dates.map(d => {
                const record = data.find(item => item.sales_date === d && item.channel === 'distributor');
                return record ? record.gross_revenue : 0;
            });

            Chart.defaults.color = '#94a3b8';
            Chart.defaults.font.family = 'Inter';

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: 'Shopify',
                            data: shopifyData,
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            borderRadius: 4
                        },
                        {
                            label: 'POS',
                            data: posData,
                            backgroundColor: 'rgba(16, 185, 129, 0.8)',
                            borderRadius: 4
                        },
                        {
                            label: 'Distributor',
                            data: distributorData,
                            backgroundColor: 'rgba(245, 158, 11, 0.8)',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                        y: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' } }
                    },
                    plugins: {
                        legend: { position: 'top' }
                    }
                }
            });
        });

    // Inventory Data
    fetch('/api/inventory')
        .then(res => res.json())
        .then(data => {
            // Sort by sales descending
            data.sort((a, b) => b.total_sales_amount - a.total_sales_amount);
            
            // Chart
            const ctx = document.getElementById('inventoryChart').getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(item => item.product_title),
                    datasets: [{
                        data: data.map(item => item.total_sales_amount),
                        backgroundColor: [
                            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right' }
                    }
                }
            });

            // Table
            const tbody = document.querySelector('#inventory-table tbody');
            data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.sku}</td>
                    <td>${item.product_title}</td>
                    <td>${item.units_sold.toLocaleString()}</td>
                    <td>₹${item.total_sales_amount.toLocaleString('en-IN', {minimumFractionDigits:2})}</td>
                `;
                tbody.appendChild(tr);
            });
        });

    // Customers Data
    fetch('/api/customers')
        .then(res => res.json())
        .then(data => {
            // Sort by total spend descending
            data.sort((a, b) => b.total_spend - a.total_spend);
            
            const tbody = document.querySelector('#customers-table tbody');
            data.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.customer_id}</td>
                    <td>${item.customer_email}</td>
                    <td>${item.total_orders}</td>
                    <td>₹${item.total_spend.toLocaleString('en-IN', {minimumFractionDigits:2})}</td>
                    <td><span class="badge">${item.preferred_channel}</span></td>
                    <td>${item.first_purchase_date}</td>
                    <td>${item.last_purchase_date}</td>
                `;
                tbody.appendChild(tr);
            });
        });
});

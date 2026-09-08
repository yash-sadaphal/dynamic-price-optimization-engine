/**
 * Dynamic Price Optimization Engine - Chart.js Visualizations
 * Handles asynchronous data fetching from Flask REST endpoints and charts rendering.
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Initialize Sales Trend Line Chart if canvas exists
    const salesCanvas = document.getElementById("salesTrendsChart");
    if (salesCanvas) {
        initSalesTrendChart(salesCanvas);
    }

    // 2. Initialize Price Comparison Bar Chart if canvas exists
    const priceCompCanvas = document.getElementById("priceComparisonChart");
    if (priceCompCanvas) {
        initPriceComparisonChart(priceCompCanvas);
    }

    // 3. Initialize Category Doughnut Chart if canvas exists
    const categoryCanvas = document.getElementById("categoryChart");
    if (categoryCanvas) {
        initCategoryChart(categoryCanvas);
    }
});

/**
 * Renders Sales Revenue & Units Sold Over Time
 */
function initSalesTrendChart(canvas) {
    fetch("/api/chart/sales-trends")
        .then(res => res.json())
        .then(data => {
            const ctx = canvas.getContext("2d");
            new Chart(ctx, {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Total Revenue ($)",
                            data: data.revenues,
                            borderColor: "#4f46e5",
                            backgroundColor: "rgba(79, 70, 229, 0.1)",
                            fill: true,
                            tension: 0.35,
                            pointRadius: 4,
                            pointBackgroundColor: "#4f46e5",
                            yAxisID: "y"
                        },
                        {
                            label: "Units Sold",
                            data: data.units,
                            borderColor: "#0ea5e9",
                            backgroundColor: "transparent",
                            borderDash: [5, 5],
                            tension: 0.35,
                            pointRadius: 3,
                            pointBackgroundColor: "#0ea5e9",
                            yAxisID: "y1"
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: "index",
                        intersect: false
                    },
                    scales: {
                        y: {
                            type: "linear",
                            display: true,
                            position: "left",
                            title: { display: true, text: "Revenue ($)" },
                            grid: { color: "#f1f5f9" }
                        },
                        y1: {
                            type: "linear",
                            display: true,
                            position: "right",
                            title: { display: true, text: "Units Sold" },
                            grid: { drawOnChartArea: false }
                        },
                        x: {
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { position: "top" }
                    }
                }
            });
        })
        .catch(err => console.error("Error loading sales chart:", err));
}

/**
 * Renders Grouped Bar Chart: Current vs Competitor vs AI Recommended Price
 */
function initPriceComparisonChart(canvas) {
    fetch("/api/chart/price-comparison")
        .then(res => res.json())
        .then(data => {
            const ctx = canvas.getContext("2d");
            new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Current Price ($)",
                            data: data.current_prices,
                            backgroundColor: "#94a3b8",
                            borderRadius: 4
                        },
                        {
                            label: "Competitor Price ($)",
                            data: data.competitor_prices,
                            backgroundColor: "#f59e0b",
                            borderRadius: 4
                        },
                        {
                            label: "AI Recommended ($)",
                            data: data.recommended_prices,
                            backgroundColor: "#10b981",
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: "Price (USD $)" },
                            grid: { color: "#f1f5f9" }
                        },
                        x: {
                            grid: { display: false },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0
                            }
                        }
                    },
                    plugins: {
                        legend: { position: "top" },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return context.dataset.label + ": $" + context.parsed.y.toFixed(2);
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(err => console.error("Error loading price comparison chart:", err));
}

/**
 * Renders Doughnut Chart: Catalog Distribution by Category
 */
function initCategoryChart(canvas) {
    fetch("/api/chart/category-distribution")
        .then(res => res.json())
        .then(data => {
            const ctx = canvas.getContext("2d");
            new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.counts,
                        backgroundColor: [
                            "#4f46e5",
                            "#0ea5e9",
                            "#10b981",
                            "#f59e0b",
                            "#ec4899",
                            "#8b5cf6"
                        ],
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom"
                        }
                    },
                    cutout: "68%"
                }
            });
        })
        .catch(err => console.error("Error loading category chart:", err));
}

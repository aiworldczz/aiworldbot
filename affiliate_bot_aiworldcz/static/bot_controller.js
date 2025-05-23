document.addEventListener('DOMContentLoaded', function() {
    const startBotBtn = document.getElementById('startBot');
    const stopBotBtn = document.getElementById('stopBot');
    const botStatusSpan = document.getElementById('botStatus');
    const logContent = document.getElementById('logContent');
    
    console.log("Bot controller initialized");
    
    // Function to update UI based on bot status
    function updateBotStatusUI(status) {
        console.log("Updating status UI to:", status);
        botStatusSpan.textContent = status;
        
        if (status === 'running') {
            botStatusSpan.className = 'badge bg-success';
            startBotBtn.disabled = true;
            stopBotBtn.disabled = false;
        } else {
            botStatusSpan.className = 'badge bg-secondary';
            startBotBtn.disabled = false;
            stopBotBtn.disabled = true;
        }
    }
    
    // Function to update log content
    function updateLogContent(logEntries) {
        if (!logEntries || logEntries.length === 0) return;
        
        // Clear existing content if there are too many entries
        if (logContent.childElementCount > 200) {
            logContent.innerHTML = '';
        }
        
        // Add new log entries
        logEntries.forEach(entry => {
            const logLine = document.createElement('div');
            logLine.textContent = entry;
            logContent.appendChild(logLine);
        });
        
        // Scroll to bottom
        const logContainer = document.getElementById('logContainer');
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // Function to poll bot status
    function pollBotStatus() {
        console.log("Polling bot status...");
        fetch('/api/bot_status')
            .then(response => response.json())
            .then(data => {
                console.log("Received status:", data);
                updateBotStatusUI(data.status);
                updateLogContent(data.log);
            })
            .catch(error => {
                console.error('Error polling bot status:', error);
            });
    }
    
    // Start polling bot status
    setInterval(pollBotStatus, 2000);
    pollBotStatus(); // Initial call
    
    // Start bot action
    if (startBotBtn) {
        console.log("Adding start button listener");
        startBotBtn.addEventListener('click', function() {
            console.log("Start button clicked");
            
            // Show immediate feedback
            const tempLogLine = document.createElement('div');
            tempLogLine.textContent = `[${new Date().toLocaleTimeString()}] Starting bot...`;
            logContent.appendChild(tempLogLine);
            
            fetch('/api/start_bot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                console.log("Start bot response:", response);
                return response.json();
            })
            .then(data => {
                console.log("Start bot data:", data);
                if (data.success) {
                    updateBotStatusUI(data.status);
                    const logLine = document.createElement('div');
                    logLine.textContent = `[${new Date().toLocaleTimeString()}] ${data.message}`;
                    logContent.appendChild(logLine);
                } else {
                    alert(`Failed to start bot: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error starting bot:', error);
                alert('Error starting bot. Check console for details.');
            });
        });
    }
    
    // Stop bot action
    if (stopBotBtn) {
        console.log("Adding stop button listener");
        stopBotBtn.addEventListener('click', function() {
            console.log("Stop button clicked");
            
            // Show immediate feedback
            const tempLogLine = document.createElement('div');
            tempLogLine.textContent = `[${new Date().toLocaleTimeString()}] Stopping bot...`;
            logContent.appendChild(tempLogLine);
            
            fetch('/api/stop_bot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                console.log("Stop bot response:", response);
                return response.json();
            })
            .then(data => {
                console.log("Stop bot data:", data);
                if (data.success) {
                    updateBotStatusUI(data.status);
                    const logLine = document.createElement('div');
                    logLine.textContent = `[${new Date().toLocaleTimeString()}] ${data.message}`;
                    logContent.appendChild(logLine);
                } else {
                    alert(`Failed to stop bot: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error stopping bot:', error);
                alert('Error stopping bot. Check console for details.');
            });
        });
    }
    
    console.log("Bot controller setup complete");
});
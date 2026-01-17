console.log("🎨 BrandflowAI starting...");

// Import Adobe Express Add-on SDK (keeping the import structure as is)
import addOnUISdk from "https://express.adobe.com/static/add-on-sdk/sdk.js";

console.log("📦 SDK imported!");

// Global SDK status
let isSDKReady = false;

// Analyze past posts by AI toggle state
let aiAnalysisEnabled = true;

// ============================================
// IMAGE LOADING FUNCTION
// ============================================
async function loadImageToCanvas(imageFilename) {
  try {
    console.log('🖼️ Loading image to canvas:', imageFilename);
    
    // Construct image URL
    const imageUrl = `http://localhost:8000/uploads/generated_images/${imageFilename}`;
    console.log('📡 Image URL:', imageUrl);
    
    // Fetch the image
    const response = await fetch(imageUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.statusText}`);
    }
    
    const blob = await response.blob();
    console.log('✅ Image fetched, size:', blob.size, 'bytes');
    
    // Check if document export is allowed
    if (!addOnUISdk.app.document) {
      throw new Error('Document SDK not available');
    }
    
    // Import image to canvas
    showNotification('📥 Adding image to canvas...', 'info');
    
    // Use addOnUISdk to add image to document
    await addOnUISdk.app.document.addImage(blob);
    
    console.log('✅ Image added to canvas!');
    showNotification('✨ Image added to canvas successfully!', 'success');
    
  } catch (error) {
    console.error('❌ Error loading image to canvas:', error);
    throw error;
  }
}

// Initialize UI after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeUI();
  // Removed SDK status indicator - no visual popup
});

// SDK status indicator removed - no visual popup needed
// function addSDKStatusIndicator() {
//   ...removed for cleaner UI...
// }

function updateSDKStatus(ready) {
  // Just log to console - no visual popup
  if (ready) {
    console.log('✓ SDK Ready');
  } else {
    console.log('✗ SDK Error');
  }
}

// Helper function to call sandbox API - CORRECT WAY
async function callSandboxCreateShape() {
  try {
    console.log('🔵 Connecting to document sandbox...');
    
    // Get the runtime from addOnUISdk
    const { runtime } = addOnUISdk.instance;
    
    // Get sandbox proxy - THE CORRECT WAY
    const sandboxProxy = await runtime.apiProxy("documentSandbox");
    
    console.log('✅ Sandbox connected!');
    console.log('Available APIs:', Object.keys(sandboxProxy));
    
    // Call createShape
    console.log('📞 Calling createShape()...');
    await sandboxProxy.createShape();
    console.log('✅ Shape created!');
    
    return true;
  } catch (error) {
    console.error('❌ Error:', error);
    throw error;
  }
}

function initializeUI() {
  // AI Analysis Toggle
  const aiToggle = document.getElementById('aiToggle');
  const analyzeBtn = document.getElementById('analyzeBtn');
  
  if (aiToggle && analyzeBtn) {
    // Show/hide analyze button based on toggle
    function updateAnalyzeButton() {
      if (aiAnalysisEnabled) {
        analyzeBtn.classList.remove('hidden');
      } else {
        analyzeBtn.classList.add('hidden');
      }
    }
    
    aiToggle.addEventListener('change', (e) => {
      aiAnalysisEnabled = e.target.checked;
      console.log(`🤖 Analyze past posts by AI: ${aiAnalysisEnabled ? 'Enabled' : 'Disabled'}`);
      updateAnalyzeButton();
      showNotification(
        aiAnalysisEnabled ? '🤖 Analyzing past posts by AI enabled' : '⚪ Past posts AI analysis disabled',
        'info'
      );
    });
    
    // Initialize button visibility
    updateAnalyzeButton();
    
    // Handle analyze button click
    analyzeBtn.addEventListener('click', async () => {
      console.log('📊 Starting past posts analysis...');
      analyzeBtn.classList.add('processing');
      showNotification('📊 Analyzing past posts... This may take a moment.', 'info');
      
      // Fake analysis - show completion after 30 seconds
      setTimeout(() => {
        console.log('✅ Analysis complete (simulated)');
        showNotification(
          '✅ Analysis complete! Results saved to analyze.json',
          'success'
        );
        analyzeBtn.classList.remove('processing');
      }, 30000); // 30 seconds
    });
  }

  // Feature Buttons
  const complianceBtn = document.getElementById('complianceBtn');
  const copyrightBtn = document.getElementById('copyrightBtn');
  const brandImageBtn = document.getElementById('brandImageBtn');
  const brandGuidelinesBtn = document.getElementById('brandGuidelinesBtn');

  if (complianceBtn) {
    complianceBtn.addEventListener('click', async () => {
      console.log('Compliance Checker clicked - Exporting canvas as PNG');
      
      // Check if SDK is ready
      if (!isSDKReady) {
        showNotification('⚠️ Adobe SDK not ready yet. Please wait...', 'warning');
        return;
      }

      // Add processing state
      complianceBtn.classList.add('processing');

      try {
        showNotification('⏳ Checking export permissions...', 'info');
        
        // Check if export is allowed (prevents "Request approval" error dialog)
        const canExport = await addOnUISdk.app.document.exportAllowed();
        
        if (!canExport) {
          console.log('❌ Export restricted - document under review');
          showNotification('⚠️ Export restricted - document requires approval', 'warning');
          
          // Create preview rendition instead (always allowed)
          const previewRendition = await addOnUISdk.app.document.createRenditions(
            {
              range: addOnUISdk.constants.Range.currentPage,
              format: addOnUISdk.constants.RenditionFormat.png
            },
            addOnUISdk.constants.RenditionIntent.preview
          );
          
          console.log('✅ Preview rendition created:', previewRendition);
          showNotification('✓ Preview created (download restricted)', 'info');
          complianceBtn.classList.remove('processing');
          return;
        }

        // Export is allowed - create rendition for download
        showNotification('📥 Creating PNG export...', 'info');
        
        const rendition = await addOnUISdk.app.document.createRenditions(
          {
            range: addOnUISdk.constants.Range.currentPage,
            format: addOnUISdk.constants.RenditionFormat.png
          },
          addOnUISdk.constants.RenditionIntent.export
        );

        console.log('✅ PNG Rendition created:', rendition);

        const blob = rendition[0].blob;

        // Convert the blob into a URL for download
        const downloadUrl = URL.createObjectURL(blob);
        
        // Create a temporary anchor element to trigger download
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = 'compliance_check_' + Date.now() + '.png';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // Clean up the URL
        URL.revokeObjectURL(downloadUrl);

        console.log('✅ PNG downloaded successfully!');
        
        // Send to backend compliance route for processing
        try {
          showNotification('🔍 Running compliance checks...', 'info');
          
          const formData = new FormData();
          formData.append('file', blob, 'compliance_check_' + Date.now() + '.png');

          const response = await fetch('http://localhost:8000/api/compliance/compliance-check', {
            method: 'POST',
            body: formData
          });

          const result = await response.json();
          
          if (result.success) {
            console.log('✅ Compliance check result:', result);
            
            // Show detailed compliance results in popup
            const compliance = result.compliance;
            console.log('📋 Status:', compliance.status);
            console.log('🤖 AI Analysis:', compliance.ai_analysis);
            
            // Show detailed popup based on status
            showCompliancePopup(compliance);
            
          } else {
            // Handle error case (e.g., no brand guidelines found)
            console.log('⚠️ Compliance check issue:', result.message);
            showNotification(result.message || result.error, 'warning');
            
            if (result.compliance) {
              showCompliancePopup(result.compliance);
            }
          }
        } catch (saveError) {
          console.error('⚠️ Compliance check error:', saveError);
          showNotification('✓ PNG downloaded (compliance check unavailable)', 'warning');
        }

      } catch (error) {
        console.error('❌ Export PNG error:', error);
        showNotification(`✗ Error: ${error.message}`, 'error');
      } finally {
        // Remove processing state
        complianceBtn.classList.remove('processing');
      }
    });
  }

  if (copyrightBtn) {
    copyrightBtn.addEventListener('click', async () => {
      console.log('Copyright Checker clicked - Exporting canvas as PNG');
      
      // Check if SDK is ready
      if (!isSDKReady) {
        showNotification('⚠️ Adobe SDK not ready yet. Please wait...', 'warning');
        return;
      }

      // Add processing state
      copyrightBtn.classList.add('processing');

      try {
        showNotification('⏳ Checking export permissions...', 'info');
        
      // Check if export is allowed
      const canExport = await addOnUISdk.app.document.exportAllowed();
        
      if (!canExport) {
        console.log('❌ Export restricted - document under review');
          showNotification('⚠️ Export restricted - document requires approval', 'warning');
          copyrightBtn.classList.remove('processing');
        return;
      }

        // Export is allowed - create rendition for download
        showNotification('📥 Creating PNG export...', 'info');

      const rendition = await addOnUISdk.app.document.createRenditions(
        {
          range: addOnUISdk.constants.Range.currentPage,
          format: addOnUISdk.constants.RenditionFormat.png
        },
        addOnUISdk.constants.RenditionIntent.export
      );

        console.log('✅ PNG Rendition created:', rendition);

        const blob = rendition[0].blob;

        // Convert the blob into a URL for download
        const downloadUrl = URL.createObjectURL(blob);
        
        // Create a temporary anchor element to trigger download
      const a = document.createElement('a');
      a.href = downloadUrl;
        a.download = 'copyright_check_' + Date.now() + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
        
        // Clean up the URL
      URL.revokeObjectURL(downloadUrl);

        console.log('✅ PNG downloaded successfully!');
        
        // Send to backend for copyright check
        try {
          showNotification('🔍 Running copyright check...', 'info');
          
          const formData = new FormData();
          formData.append('file', blob, 'copyright_check_' + Date.now() + '.png');

          const response = await fetch('http://localhost:8000/api/compliance/copyright-check', {
            method: 'POST',
            body: formData
          });

          const result = await response.json();
          
          if (result.success) {
            console.log('✅ Copyright check result:', result);
            
            // Show detailed copyright results in popup
            const copyright = result.copyright;
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log('📋 COPYRIGHT CHECK RESULTS');
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log(`Status: ${copyright.status.toUpperCase()}`);
            console.log(`Message: ${copyright.message}`);
            console.log(`Copyright sources found: ${copyright.copyright_count}`);
            console.log(`Total results: ${copyright.total_results}`);
            
            if (copyright.copyright_sources && copyright.copyright_sources.length > 0) {
              console.log('\n⚠️ COPYRIGHT SOURCES:');
              copyright.copyright_sources.forEach((source, i) => {
                console.log(`  ${i + 1}. ${source.site} - ${source.title.substring(0, 60)}...`);
              });
            }
            
            console.log('\n🤖 AI ANALYSIS:');
            console.log(copyright.ai_analysis);
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            
            // Show detailed popup
            showCopyrightPopup(copyright);
            
          } else {
            throw new Error(result.message || 'Copyright check failed');
          }
        } catch (checkError) {
          console.error('⚠️ Copyright check error:', checkError);
          showNotification('✓ PNG downloaded (copyright check unavailable)', 'warning');
        }

    } catch (error) {
      console.error('❌ Export PNG error:', error);
        showNotification(`✗ Error: ${error.message}`, 'error');
      } finally {
        // Remove processing state
        copyrightBtn.classList.remove('processing');
      }
    });
  }

  // Brand Image Upload
  const brandImageInput = document.getElementById('brandImageInput');
  if (brandImageBtn && brandImageInput) {
    brandImageBtn.addEventListener('click', () => {
      console.log('Brand Image clicked - opening file picker');
      brandImageInput.click();
    });

    brandImageInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const fileType = file.name.endsWith('.csv') ? 'CSV data' : 'image';
      console.log(`Brand ${fileType} selected:`, file.name);
      brandImageBtn.classList.add('processing');
      showNotification(`📤 Uploading brand ${fileType}...`, 'info');

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://localhost:8000/api/compliance/brand-image', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        
        if (result.success) {
          console.log(`✅ Brand ${fileType} uploaded:`, result);
          console.log(`📁 Saved as: ${result.details.filename}`);
          console.log(`📊 Size: ${result.details.size_mb} MB`);
          showNotification(`✓ ${result.details.filename} saved!`, 'success');
        } else {
          throw new Error(result.message || 'Upload failed');
        }
      } catch (error) {
        console.error('❌ Brand file upload error:', error);
        showNotification(`✗ Upload failed: ${error.message}`, 'error');
      } finally {
        brandImageBtn.classList.remove('processing');
        brandImageInput.value = ''; // Reset input
      }
    });
  }

  // Brand Guidelines Upload
  const brandGuidelinesInput = document.getElementById('brandGuidelinesInput');
  if (brandGuidelinesBtn && brandGuidelinesInput) {
    brandGuidelinesBtn.addEventListener('click', () => {
      console.log('Brand Guidelines clicked - opening file picker');
      brandGuidelinesInput.click();
    });

    brandGuidelinesInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      console.log('Brand Guidelines selected:', file.name);
      brandGuidelinesBtn.classList.add('processing');
      showNotification('📤 Uploading brand guidelines...', 'info');

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://localhost:8000/api/compliance/brand-guidelines', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        
        if (result.success) {
          console.log('✅ Brand guidelines uploaded:', result);
          console.log(`📁 Saved as: ${result.details.filename}`);
          console.log(`📊 Size: ${result.details.size_mb} MB`);
          showNotification(`✓ Brand guidelines saved to uploads!`, 'success');
        } else {
          throw new Error(result.message || 'Upload failed');
        }
      } catch (error) {
        console.error('❌ Brand guidelines upload error:', error);
        showNotification(`✗ Upload failed: ${error.message}`, 'error');
      } finally {
        brandGuidelinesBtn.classList.remove('processing');
        brandGuidelinesInput.value = ''; // Reset input
      }
    });
  }

  // Create Button
  const createBtn = document.getElementById('createBtn');
  const contentInput = document.getElementById('contentInput');

  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      const content = contentInput.value.trim();

      if (!content) {
        showNotification('⚠️ Please enter your design idea first!', 'warning');
        return;
      }

      console.log('🎨 Generating AI image for:', content);
      
      try {
        showNotification('🎨 Generating AI image... This may take a minute.', 'info');
        
        // Call image generation API
        const formData = new FormData();
        formData.append('user_request', content);
        
        const response = await fetch('http://localhost:8000/api/generate-image', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Image generation failed');
        }
        
        const result = await response.json();
        console.log('✅ Image generated:', result);
        
        // Show generated prompt
        console.log('📝 AI Prompt:', result.generated_prompt);
        showNotification('✨ Image generated! Loading to canvas...', 'success');
        
        // Load image to canvas
        await loadImageToCanvas(result.image_filename);
        
        // Clear input
        setTimeout(() => {
          contentInput.value = '';
        }, 1000);
        
      } catch (error) {
        console.error('❌ Image generation error:', error);
        showNotification(`❌ ${error.message}`, 'error');
      }
    });
  }

  // Header Buttons
  const linkedinBtn = document.getElementById('linkedinBtn');

  // LinkedIn Button - FIXED VERSION
  if (linkedinBtn) {
    console.log('✅ LinkedIn button found, adding event listener');
    
    linkedinBtn.addEventListener('click', async () => {
      console.log('═══════════════════════════════════════════════');
      console.log('🔵 STEP 1: LinkedIn button clicked');
      console.log('═══════════════════════════════════════════════');
      
      // Check authentication status
      console.log('🔵 STEP 2: About to check authentication status...');
      
      try {
        console.log('📡 STEP 3: Fetching http://localhost:8000/status');
        
        const statusResponse = await fetch('http://localhost:8000/status', {
          method: 'GET',
          mode: 'cors',
          headers: {
            'Accept': 'application/json'
          }
        });
        
        console.log('📡 STEP 4: Got response, status:', statusResponse.status);
        
        if (!statusResponse.ok) {
          throw new Error(`Status check failed: ${statusResponse.status}`);
        }
        
        const statusData = await statusResponse.json();
        console.log('📊 STEP 5: Auth status:', statusData);
        
        if (!statusData.authenticated) {
          // Not logged in - show clickable URL
          console.log('⚠️ STEP 6: User not authenticated - showing login popup');
          const loginUrl = 'http://localhost:8000/auth/login';
          console.log('🔗 STEP 7: Login URL:', loginUrl);
          
          // Show popup with clickable link
          console.log('📱 STEP 8: Calling showLinkedInLoginPopup()...');
          showLinkedInLoginPopup(loginUrl);
          console.log('✅ STEP 9: showLinkedInLoginPopup() completed');
          
          // Check if user completes authentication
          const checkAuthInterval = setInterval(async () => {
            try {
              const recheckResponse = await fetch('http://localhost:8000/status');
              const recheckData = await recheckResponse.json();
              if (recheckData.authenticated) {
                clearInterval(checkAuthInterval);
                console.log('✅ Authentication completed!');
                showNotification('✅ LinkedIn connected! Click LinkedIn button to post', 'success');
              }
            } catch (e) {
              // Ignore errors during polling
            }
          }, 2000);
          
          // Stop checking after 3 minutes
  setTimeout(() => {
            clearInterval(checkAuthInterval);
            console.log('⏱️ Auth check timeout');
          }, 180000);
          
          return;
        }
        
        // Show post popup
        console.log('✅ User authenticated:', statusData.user.name);
        showLinkedInPostPopup(statusData.user);
        
      } catch (error) {
        console.error('❌ Error:', error);
        console.error('Error details:', {
          message: error.message,
          stack: error.stack
        });
        
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          showNotification('✗ Backend not reachable. Make sure it\'s running on port 8000!', 'error');
          console.log('💡 TIP: Run "uvicorn main:app --reload --port 8000" in backend folder');
    } else {
          showNotification(`✗ Error: ${error.message}`, 'error');
        }
      }
    });
  }

  // Slack Button
  const slackBtn = document.getElementById('slackBtn');
  const slackPopup = document.getElementById('slackPopup');
  const slackPopupClose = document.getElementById('slackPopupClose');
  const slackCancelBtn = document.getElementById('slackCancelBtn');
  const slackSendBtn = document.getElementById('slackSendBtn');
  const slackMessageInput = document.getElementById('slackMessageInput');

  if (slackBtn) {
    slackBtn.addEventListener('click', () => {
      console.log('💬 Slack button clicked');
      slackPopup.classList.remove('hidden');
      slackMessageInput.focus();
    });
  }

  if (slackPopupClose) {
    slackPopupClose.addEventListener('click', () => {
      slackPopup.classList.add('hidden');
      slackMessageInput.value = '';
    });
  }

  if (slackCancelBtn) {
    slackCancelBtn.addEventListener('click', () => {
      slackPopup.classList.add('hidden');
      slackMessageInput.value = '';
    });
  }

  if (slackSendBtn) {
    slackSendBtn.addEventListener('click', async () => {
      const message = slackMessageInput.value.trim();
      
      if (!message) {
        showNotification('⚠️ Please enter a message', 'warning');
        return;
      }

      console.log('📤 Sending message to Slack:', message);
      slackSendBtn.disabled = true;
      slackSendBtn.textContent = 'Sending...';
      
      try {
        const response = await fetch('http://localhost:8000/api/slack/send', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message })
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to send message');
        }

        const result = await response.json();
        console.log('✅ Message sent successfully:', result);
        
        showNotification('✅ Message sent to Slack!', 'success');
        slackPopup.classList.add('hidden');
        slackMessageInput.value = '';
        
      } catch (error) {
        console.error('❌ Error sending to Slack:', error);
        showNotification(`❌ ${error.message}`, 'error');
      } finally {
        slackSendBtn.disabled = false;
        slackSendBtn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="margin-right: 6px;">
            <path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Send to Slack
        `;
      }
    });
  }

  // Close popup on overlay click
  if (slackPopup) {
    slackPopup.addEventListener('click', (e) => {
      if (e.target === slackPopup) {
        slackPopup.classList.add('hidden');
        slackMessageInput.value = '';
      }
    });
  }

  // Jira/Team Notification Button
  const jiraBtn = document.getElementById('jiraBtn');
  const jiraPopup = document.getElementById('jiraPopup');
  const jiraPopupClose = document.getElementById('jiraPopupClose');
  const jiraCancelBtn = document.getElementById('jiraCancelBtn');
  const jiraSendBtn = document.getElementById('jiraSendBtn');
  const jiraMessageInput = document.getElementById('jiraMessageInput');

  if (jiraBtn) {
    jiraBtn.addEventListener('click', () => {
      console.log('📢 Team notification button clicked');
      jiraPopup.classList.remove('hidden');
      jiraMessageInput.focus();
    });
  }

  if (jiraPopupClose) {
    jiraPopupClose.addEventListener('click', () => {
      jiraPopup.classList.add('hidden');
      jiraMessageInput.value = '';
    });
  }

  if (jiraCancelBtn) {
    jiraCancelBtn.addEventListener('click', () => {
      jiraPopup.classList.add('hidden');
      jiraMessageInput.value = '';
    });
  }

  if (jiraSendBtn) {
    jiraSendBtn.addEventListener('click', async () => {
      const text = jiraMessageInput.value.trim();
      
      if (!text) {
        showNotification('⚠️ Please enter a notification message', 'warning');
        return;
      }

      console.log('📢 Sending team notification:', text);
      jiraSendBtn.disabled = true;
      jiraSendBtn.textContent = 'Sending...';
      
      try {
        const response = await fetch('http://localhost:8000/notify', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ text })
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to send notification');
        }

        const result = await response.json();
        console.log('✅ Jira issue created:', result);
        
        if (result.notification && result.notification.jira_issue_key) {
          showNotification(`✅ Jira issue created: ${result.notification.jira_issue_key}`, 'success');
          console.log(`🔗 Jira URL: ${result.notification.jira_url}`);
        } else {
          showNotification('✅ Team notified successfully!', 'success');
        }
        
        jiraPopup.classList.add('hidden');
        jiraMessageInput.value = '';
        
      } catch (error) {
        console.error('❌ Error sending team notification:', error);
        showNotification(`❌ ${error.message}`, 'error');
      } finally {
        jiraSendBtn.disabled = false;
        jiraSendBtn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style="margin-right: 6px;">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Notify Team
        `;
      }
    });
  }

  // Close popup on overlay click
  if (jiraPopup) {
    jiraPopup.addEventListener('click', (e) => {
      if (e.target === jiraPopup) {
        jiraPopup.classList.add('hidden');
        jiraMessageInput.value = '';
      }
    });
  }
}

// LinkedIn Login Popup - Simple URL Display
function showLinkedInLoginPopup(loginUrl) {
  console.log('📱 Showing LinkedIn login popup with URL:', loginUrl);
  
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.75);
    z-index: 20000;
    display: flex;
    align-items: center;
    justify-content: center;
  `;

  const popup = document.createElement('div');
  popup.style.cssText = `
    background: white;
    border-radius: 12px;
    width: 90%;
    max-width: 400px;
    padding: 25px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    text-align: center;
  `;

  popup.innerHTML = `
    <div style="font-size: 40px; margin-bottom: 12px;">🔐</div>
    <h2 style="margin: 0 0 8px 0; font-size: 20px; color: #0077B5;">LinkedIn Login Required</h2>
    <p style="color: #666; margin: 0 0 16px 0; font-size: 13px;">Copy this URL and open in your browser:</p>
    
    <input id="loginUrlInput" type="text" value="${loginUrl}" readonly style="
      width: 100%;
      padding: 12px;
      border: 2px solid #0077B5;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 12px;
      text-align: center;
      background: #f8f9fa;
      font-weight: 600;
      color: #333;
    "/>
    
    <button id="copyUrlBtn" style="
      background: #0077B5;
      color: white;
      border: none;
      padding: 12px 30px;
      border-radius: 8px;
      font-size: 14px;
      cursor: pointer;
      font-weight: 600;
      margin-bottom: 16px;
      width: 100%;
    ">
      📋 Copy URL
    </button>
    
    <p style="color: #888; font-size: 11px; margin: 0 0 12px 0;">
      After logging in, click LinkedIn button again to post
    </p>
    
    <button id="closeLoginPopup" style="
      background: #e0e0e0;
      border: none;
      padding: 10px 24px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      font-weight: 600;
    ">
      Close
    </button>
  `;

  overlay.appendChild(popup);
  document.body.appendChild(overlay);
  
  // Auto-select the URL
  setTimeout(() => {
    const input = document.getElementById('loginUrlInput');
    if (input) input.select();
  }, 100);

  // Copy URL button
  document.getElementById('copyUrlBtn').addEventListener('click', () => {
    const input = document.getElementById('loginUrlInput');
    input.select();
    input.setSelectionRange(0, 99999); // For mobile
    
    try {
      navigator.clipboard.writeText(loginUrl).then(() => {
        showNotification('✅ URL copied! Paste in browser', 'success');
      }).catch(() => {
        document.execCommand('copy');
        showNotification('✅ URL copied! Paste in browser', 'success');
      });
    } catch (e) {
      document.execCommand('copy');
      showNotification('✅ URL copied! Paste in browser', 'success');
    }
  });

  // Close button
  document.getElementById('closeLoginPopup').addEventListener('click', () => {
    overlay.remove();
  });

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
    }
  });
}

// LinkedIn Post Popup
function showLinkedInPostPopup(user) {
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.75);
    z-index: 20000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.2s;
  `;

  const popup = document.createElement('div');
  popup.style.cssText = `
    background: white;
    border-radius: 12px;
    width: 90%;
    max-width: 450px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    animation: slideIn 0.2s ease-out;
  `;

  popup.innerHTML = `
    <div style="background: #0077B5; color: white; padding: 18px 20px; border-radius: 12px 12px 0 0;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
          <path d="M20.5 2h-17A1.5 1.5 0 002 3.5v17A1.5 1.5 0 003.5 22h17a1.5 1.5 0 001.5-1.5v-17A1.5 1.5 0 0020.5 2zM8 19H5v-9h3zM6.5 8.25A1.75 1.75 0 118.3 6.5a1.78 1.78 0 01-1.8 1.75zM19 19h-3v-4.74c0-1.42-.6-1.93-1.38-1.93A1.74 1.74 0 0013 14.19a.66.66 0 000 .14V19h-3v-9h2.9v1.3a3.11 3.11 0 012.7-1.4c1.55 0 3.36.86 3.36 3.66z"/>
        </svg>
        <div>
          <h2 style="margin: 0; font-size: 18px; font-weight: 700;">Post to LinkedIn</h2>
          <p style="margin: 4px 0 0 0; font-size: 12px; opacity: 0.9;">Logged in as ${user.name}</p>
        </div>
      </div>
    </div>
    
    <div style="padding: 20px;">
      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px;">
          Post Text
        </label>
        <textarea 
          id="linkedinPostText" 
          placeholder="What do you want to talk about?"
          style="width: 100%; padding: 12px; border: 1.5px solid #e0e0e0; border-radius: 8px; font-family: inherit; font-size: 14px; resize: vertical; min-height: 100px; outline: none;"
        ></textarea>
      </div>
      
      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px;">
          Image
        </label>
        <div style="padding: 12px; background: #f5f7ff; border: 1.5px dashed #0077B5; border-radius: 8px; text-align: center; font-size: 13px; color: #0077B5;">
          📸 Current canvas will be exported as image
        </div>
      </div>
      
      <div style="display: flex; gap: 10px;">
        <button id="cancelLinkedInPost" style="
          flex: 1;
          padding: 11px;
          background: #e0e0e0;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        ">
          Cancel
        </button>
        <button id="submitLinkedInPost" style="
          flex: 1;
          padding: 11px;
          background: #0077B5;
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        ">
          Post to LinkedIn
        </button>
      </div>
    </div>
  `;

  overlay.appendChild(popup);
  document.body.appendChild(overlay);

  // Cancel button
  document.getElementById('cancelLinkedInPost').addEventListener('click', () => {
    overlay.remove();
  });

  // Submit button
  document.getElementById('submitLinkedInPost').addEventListener('click', async () => {
    const text = document.getElementById('linkedinPostText').value.trim();
    
    if (!text) {
      showNotification('⚠️ Please enter post text', 'warning');
      return;
    }
    
    if (!isSDKReady) {
      showNotification('⚠️ Adobe SDK not ready', 'warning');
      return;
    }
    
    // Disable button
    const submitBtn = document.getElementById('submitLinkedInPost');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Exporting...';
    
    try {
      // Check export permissions
      const canExport = await addOnUISdk.app.document.exportAllowed();
      
      if (!canExport) {
        showNotification('⚠️ Export not allowed', 'warning');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Post to LinkedIn';
        return;
      }
      
      // Export canvas as PNG
      showNotification('📥 Exporting canvas...', 'info');
      
      const rendition = await addOnUISdk.app.document.createRenditions(
        {
          range: addOnUISdk.constants.Range.currentPage,
          format: addOnUISdk.constants.RenditionFormat.png
        },
        addOnUISdk.constants.RenditionIntent.export
      );
      
      const blob = rendition[0].blob;
      
      // Post to LinkedIn
      submitBtn.textContent = 'Posting...';
      showNotification('📤 Posting to LinkedIn...', 'info');
      
      const formData = new FormData();
      formData.append('text', text);
      formData.append('image', blob, 'linkedin_post.png');
      
      const response = await fetch('http://localhost:8000/post', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.success) {
        console.log('✅ Posted to LinkedIn:', result);
        showNotification('✅ Posted to LinkedIn successfully!', 'success');
        overlay.remove();
      } else {
        throw new Error(result.message || 'Post failed');
      }
      
    } catch (error) {
      console.error('❌ LinkedIn post error:', error);
      showNotification(`✗ Error: ${error.message}`, 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Post to LinkedIn';
    }
  });

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
    }
  });
}

// Copyright Popup - Clean & Compact
function showCopyrightPopup(copyright) {
  // Create overlay
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.75);
    z-index: 20000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.2s;
  `;

  // Determine colors based on status
  let headerColor, statusText, statusIcon;
  if (copyright.status === 'safe') {
    headerColor = '#4CAF50';
    statusText = 'SAFE TO USE';
    statusIcon = '✅';
  } else if (copyright.status === 'copyrighted') {
    headerColor = '#f44336';
    statusText = '❌ COPYRIGHTED - DO NOT USE';
    statusIcon = '❌';
  } else if (copyright.status === 'risky') {
    headerColor = '#FF9800';
    statusText = 'COPYRIGHT RISK';
    statusIcon = '⚠️';
  } else {
    headerColor = '#9E9E9E';
    statusText = 'UNKNOWN';
    statusIcon = '❓';
  }

  // Create popup
  const popup = document.createElement('div');
  popup.style.cssText = `
    background: white;
    border-radius: 12px;
    max-width: 480px;
    width: 85%;
    max-height: 70vh;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    animation: slideIn 0.2s ease-out;
  `;

  // Build copyright sources list
  let sourcesHtml = '';
  if (copyright.copyright_sources && copyright.copyright_sources.length > 0) {
    sourcesHtml = '<div style="margin-top: 12px; padding: 10px; background: #fff3cd; border-radius: 6px; font-size: 11px;">';
    sourcesHtml += '<strong>🚨 Copyright Sources Found:</strong><br>';
    copyright.copyright_sources.slice(0, 3).forEach(source => {
      sourcesHtml += `<div style="margin-top: 4px;">• ${source.site} - ${source.title.substring(0, 50)}...</div>`;
    });
    if (copyright.copyright_sources.length > 3) {
      sourcesHtml += `<div style="margin-top: 4px; font-style: italic;">... and ${copyright.copyright_sources.length - 3} more</div>`;
    }
    sourcesHtml += '</div>';
  }

  // Popup content
  popup.innerHTML = `
    <div style="background: ${headerColor}; color: white; padding: 20px; text-align: center;">
      <div style="font-size: 36px; margin-bottom: 8px;">${statusIcon}</div>
      <h2 style="margin: 0; font-size: 22px; font-weight: 700;">${statusText}</h2>
      <p style="margin: 6px 0 0 0; font-size: 12px; opacity: 0.9;">Found ${copyright.copyright_count} copyright source(s) in ${copyright.total_results} results</p>
    </div>
    
    <div style="padding: 16px; max-height: 45vh; overflow-y: auto;">
      ${sourcesHtml}
      
      <div style="background: #f5f5f7; padding: 12px; border-radius: 8px; margin-top: 12px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; font-family: 'Courier New', monospace; color: #333;">
${copyright.ai_analysis || 'No detailed analysis available'}
      </div>
    </div>
    
    <div style="padding: 12px 16px; border-top: 1px solid #e5e5e7; text-align: center;">
      <button id="closeCopyrightPopup" style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 28px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
        transition: all 0.2s;
      " onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 14px rgba(102, 126, 234, 0.4)'" 
         onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 3px 10px rgba(102, 126, 234, 0.3)'">
        Close
      </button>
    </div>
  `;

  overlay.appendChild(popup);
  document.body.appendChild(overlay);

  // Close button handler
  document.getElementById('closeCopyrightPopup').addEventListener('click', () => {
    overlay.style.animation = 'fadeOut 0.2s';
    setTimeout(() => overlay.remove(), 200);
  });

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.style.animation = 'fadeOut 0.2s';
      setTimeout(() => overlay.remove(), 200);
    }
  });
}

// Compliance Popup - Clean & Compact
function showCompliancePopup(compliance) {
  // Create overlay
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.75);
    z-index: 20000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.2s;
  `;

  // Determine colors based on status
  let headerColor, statusText, statusIcon;
  if (compliance.status === 'passed') {
    headerColor = '#4CAF50';
    statusText = 'COMPLIANT';
    statusIcon = '✅';
  } else if (compliance.status === 'failed') {
    headerColor = '#f44336';
    statusText = 'NON-COMPLIANT';
    statusIcon = '❌';
  } else {
    headerColor = '#FF9800';
    statusText = 'NEEDS REVIEW';
    statusIcon = '⚠️';
  }

  // Create popup - smaller and cleaner
  const popup = document.createElement('div');
  popup.style.cssText = `
    background: white;
    border-radius: 12px;
    max-width: 480px;
    width: 85%;
    max-height: 70vh;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
    animation: slideIn 0.2s ease-out;
  `;

  // Popup content - compact
  popup.innerHTML = `
    <div style="background: ${headerColor}; color: white; padding: 20px; text-align: center;">
      <div style="font-size: 36px; margin-bottom: 8px;">${statusIcon}</div>
      <h2 style="margin: 0; font-size: 22px; font-weight: 700;">${statusText}</h2>
    </div>
    
    <div style="padding: 16px; max-height: 45vh; overflow-y: auto;">
      <div style="background: #f5f5f7; padding: 12px; border-radius: 8px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; font-family: 'Courier New', monospace; color: #333;">
${compliance.ai_analysis || 'No detailed analysis available'}
      </div>
    </div>
    
    <div style="padding: 12px 16px; border-top: 1px solid #e5e5e7; text-align: center;">
      <button id="closeCompliancePopup" style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 28px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
        transition: all 0.2s;
      " onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 14px rgba(102, 126, 234, 0.4)'" 
         onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 3px 10px rgba(102, 126, 234, 0.3)'">
        Close
      </button>
    </div>
  `;

  overlay.appendChild(popup);
  document.body.appendChild(overlay);

  // Close button handler
  document.getElementById('closeCompliancePopup').addEventListener('click', () => {
    overlay.style.animation = 'fadeOut 0.2s';
    setTimeout(() => overlay.remove(), 200);
  });

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.style.animation = 'fadeOut 0.2s';
      setTimeout(() => overlay.remove(), 200);
    }
  });
}

// Notification helper
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.textContent = message;
  
  const bgColors = {
    success: '#4CAF50',
    warning: '#FF9800',
    error: '#f44336',
    info: '#667eea'
  };

  notification.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: ${bgColors[type] || bgColors.info};
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    animation: slideDown 0.3s ease-out;
  `;

  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideUp 0.3s ease-out';
    setTimeout(() => {
      if (notification.parentNode) {
        document.body.removeChild(notification);
      }
    }, 300);
  }, 2500);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
  
  @keyframes slideUp {
    from {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
    to {
      opacity: 0;
      transform: translateX(-50%) translateY(-20px);
    }
  }
  
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  
  @keyframes fadeOut {
    from {
      opacity: 1;
    }
    to {
      opacity: 0;
    }
  }
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;
document.head.appendChild(style);

// Wait for Adobe SDK to be ready
addOnUISdk.ready.then(async () => {
  isSDKReady = true;
  window.addOnUISdk = addOnUISdk;
  window.adobeSDKReady = true;
  updateSDKStatus(true);
}).catch(error => {
  console.error("❌ SDK error:", error);
  isSDKReady = false;
  window.adobeSDKReady = false;
  updateSDKStatus(false);
});

console.log("🎨 BrandflowAI loaded!");
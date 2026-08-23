import React, { useEffect, useRef, useState, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Heart,
  AlertTriangle,
  Building2,
  Navigation,
  Search,
  Filter,
  Layers,
  Phone,
  Zap,
  Activity,
  Compass,
  Crosshair
} from 'lucide-react';

// Blood Compatibility Matrix
const COMPATIBILITY_MAP = {
  'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'], // Universal donor
  'O+': ['O+', 'A+', 'B+', 'AB+'],
  'A-': ['A-', 'A+', 'AB-', 'AB+'],
  'A+': ['A+', 'AB+'],
  'B-': ['B-', 'B+', 'AB-', 'AB+'],
  'B+': ['B+', 'AB+'],
  'AB-': ['AB-', 'AB+'],
  'AB+': ['AB+'] // Universal recipient for receiving, only AB+ for donating
};

const isBloodCompatible = (donorGroup, patientGroup) => {
  if (!donorGroup || !patientGroup) return false;
  const cleanDonor = donorGroup.trim().toUpperCase();
  const cleanPatient = patientGroup.trim().toUpperCase();
  if (cleanDonor === cleanPatient) return true;
  const canDonateTo = COMPATIBILITY_MAP[cleanDonor] || [];
  return canDonateTo.includes(cleanPatient);
};

// Standard Central Metropolitan Coordinates & Neighborhood Anchors
const BASE_LAT = 12.9716;
const BASE_LNG = 77.5946;

const KNOWN_ANCHORS = {
  'downtown': { lat: 12.9750, lng: 77.5990 },
  'city center': { lat: 12.9716, lng: 77.5946 },
  'uptown': { lat: 12.9980, lng: 77.5890 },
  'midtown': { lat: 12.9650, lng: 77.6100 },
  'westside': { lat: 12.9590, lng: 77.5450 },
  'east end': { lat: 12.9780, lng: 77.6400 },
  'eastside': { lat: 12.9780, lng: 77.6400 },
  'central': { lat: 12.9730, lng: 77.6010 },
  'north district': { lat: 13.0200, lng: 77.5900 },
  'south district': { lat: 12.9200, lng: 77.5850 },
  'indiranagar': { lat: 12.9784, lng: 77.6408 },
  'koramangala': { lat: 12.9352, lng: 77.6245 },
  'whitefield': { lat: 12.9698, lng: 77.7500 },
  'jayanagar': { lat: 12.9308, lng: 77.5838 },
  'hsr layout': { lat: 12.9121, lng: 77.6446 },
  'electronic city': { lat: 12.8399, lng: 77.6770 },
  'malleshwaram': { lat: 13.0031, lng: 77.5643 },
  'rajajinagar': { lat: 12.9982, lng: 77.5530 },
  'hebbal': { lat: 13.0358, lng: 77.5970 },
  'mg road': { lat: 12.9740, lng: 77.6100 },
  '123 main st': { lat: 12.9745, lng: 77.6020 },
  '456 oak ave': { lat: 12.9680, lng: 77.5880 },
  '321 elm st': { lat: 12.9820, lng: 77.6150 },
  '654 maple dr': { lat: 12.9550, lng: 77.6250 },
  '789 pine rd': { lat: 12.9420, lng: 77.5790 }
};

// Deterministic coordinate generator for arbitrary addresses with smooth natural clustering
const resolveCoordinates = (addressOrLocation, idSeed = 1) => {
  if (!addressOrLocation) {
    return {
      lat: BASE_LAT + ((idSeed * 17) % 30 - 15) * 0.003,
      lng: BASE_LNG + ((idSeed * 23) % 30 - 15) * 0.003
    };
  }

  const clean = addressOrLocation.toLowerCase().trim();

  for (const [key, coords] of Object.entries(KNOWN_ANCHORS)) {
    if (clean.includes(key)) {
      // Add slight jitter for unique placement of multiple entities in the same neighborhood
      const jitterLat = (((idSeed * 13) % 11) - 5) * 0.0018;
      const jitterLng = (((idSeed * 19) % 11) - 5) * 0.0018;
      return {
        lat: Number((coords.lat + jitterLat).toFixed(6)),
        lng: Number((coords.lng + jitterLng).toFixed(6))
      };
    }
  }

  // Hash unknown string to stable coordinate in metro region
  let hash = 0;
  for (let i = 0; i < clean.length; i++) {
    hash = (hash << 5) - hash + clean.charCodeAt(i);
    hash |= 0;
  }
  const offsetLat = ((Math.abs(hash * 31 + idSeed) % 100) / 100 - 0.5) * 0.08;
  const offsetLng = ((Math.abs(hash * 67 + idSeed) % 100) / 100 - 0.5) * 0.08;

  return {
    lat: Number((BASE_LAT + offsetLat).toFixed(6)),
    lng: Number((BASE_LNG + offsetLng).toFixed(6))
  };
};

// Haversine distance calculator (in kilometers)
const calculateDistanceKm = (lat1, lon1, lat2, lon2) => {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Number((R * c).toFixed(1));
};

const LiveNetworkMap = ({
  donors = [],
  requests = [],
  bloodBanks = [],
  hospitals = [],
  currentUser = null
}) => {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);
  const routesLayerRef = useRef(null);
  const userMarkerRef = useRef(null);

  // Filter States
  const [selectedLayer, setSelectedLayer] = useState('all'); // 'all' | 'donors' | 'requests' | 'bloodbanks'
  const [selectedBloodGroup, setSelectedBloodGroup] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all' | 'pending'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [isLocating, setIsLocating] = useState(false);

  // Process Geocoded Donors
  const geocodedDonors = useMemo(() => {
    return (donors || []).map(d => {
      const coords = resolveCoordinates(d.Address || 'City Center', d.DonorID || 1);
      return {
        ...d,
        lat: coords.lat,
        lng: coords.lng,
        entityType: 'donor'
      };
    });
  }, [donors]);

  // Process Geocoded Needed Locations (Emergency Blood Requests)
  const geocodedRequests = useMemo(() => {
    return (requests || []).map(r => {
      const locationString = r.HospitalLocation || r.BloodBankLocation || 'Downtown';
      const coords = resolveCoordinates(locationString, (r.RequestID || 1) * 3);
      return {
        ...r,
        lat: coords.lat,
        lng: coords.lng,
        entityType: 'request'
      };
    });
  }, [requests]);

  // Process Geocoded Blood Banks
  const geocodedBloodBanks = useMemo(() => {
    return (bloodBanks || []).map(b => {
      const coords = resolveCoordinates(b.Location || 'City Center', (b.BloodBankID || 1) * 7);
      return {
        ...b,
        lat: coords.lat,
        lng: coords.lng,
        entityType: 'bloodbank'
      };
    });
  }, [bloodBanks]);

  // Filtered Donors
  const filteredDonors = useMemo(() => {
    return geocodedDonors.filter(d => {
      if (selectedLayer !== 'all' && selectedLayer !== 'donors') return false;
      if (selectedBloodGroup !== 'ALL' && d.BloodGroup !== selectedBloodGroup) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchName = (d.DonorName || '').toLowerCase().includes(q);
        const matchBg = (d.BloodGroup || '').toLowerCase().includes(q);
        const matchAddr = (d.Address || '').toLowerCase().includes(q);
        if (!matchName && !matchBg && !matchAddr) return false;
      }
      return true;
    });
  }, [geocodedDonors, selectedLayer, selectedBloodGroup, searchQuery]);

  // Filtered Emergency Needed Locations
  const filteredRequests = useMemo(() => {
    return geocodedRequests.filter(r => {
      if (selectedLayer !== 'all' && selectedLayer !== 'requests') return false;
      if (statusFilter === 'pending' && r.Status !== 'Pending') return false;
      if (selectedBloodGroup !== 'ALL' && r.BloodGroupRequired !== selectedBloodGroup) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchHospital = (r.HospitalName || '').toLowerCase().includes(q);
        const matchPatient = (r.PatientName || '').toLowerCase().includes(q);
        const matchBg = (r.BloodGroupRequired || '').toLowerCase().includes(q);
        if (!matchHospital && !matchPatient && !matchBg) return false;
      }
      return true;
    });
  }, [geocodedRequests, selectedLayer, statusFilter, selectedBloodGroup, searchQuery]);

  // Filtered Blood Banks
  const filteredBloodBanks = useMemo(() => {
    return geocodedBloodBanks.filter(b => {
      if (selectedLayer !== 'all' && selectedLayer !== 'bloodbanks') return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchName = (b.BloodBankName || '').toLowerCase().includes(q);
        const matchLoc = (b.Location || '').toLowerCase().includes(q);
        if (!matchName && !matchLoc) return false;
      }
      return true;
    });
  }, [geocodedBloodBanks, selectedLayer, searchQuery]);

  // Compatible Donors for Currently Selected Emergency Request
  const compatibleDonorsForSelected = useMemo(() => {
    if (!selectedRequest) return [];
    const neededBg = selectedRequest.BloodGroupRequired;
    return geocodedDonors
      .filter(d => isBloodCompatible(d.BloodGroup, neededBg))
      .map(d => {
        const distance = calculateDistanceKm(selectedRequest.lat, selectedRequest.lng, d.lat, d.lng);
        const travelMinutes = Math.max(4, Math.round(distance * 2.4));
        return {
          ...d,
          distance,
          travelMinutes
        };
      })
      .sort((a, b) => a.distance - b.distance);
  }, [selectedRequest, geocodedDonors]);

  // 1. Initialize Map Instance
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [BASE_LAT, BASE_LNG],
        zoom: 12,
        zoomControl: true,
        scrollWheelZoom: true
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
      }).addTo(map);

      markersLayerRef.current = L.layerGroup().addTo(map);
      routesLayerRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // 2. Render Markers on Layer Updates
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    markersLayer.clearLayers();

    const bounds = L.latLngBounds();
    let hasPoints = false;

    // A) Render Needed Locations / Emergency Blood Requests (Crimson Alert Beacon)
    filteredRequests.forEach(req => {
      const isSelected = selectedRequest && selectedRequest.RequestID === req.RequestID;
      const isPending = req.Status === 'Pending';

      const iconHtml = `
        <div class="map-marker-pin request ${isSelected ? 'selected' : ''} ${isPending ? 'pending-pulse' : ''}" title="Needed: ${req.BloodGroupRequired}">
          <div class="pin-badge bg-red">${req.BloodGroupRequired}</div>
          <div class="pin-icon req-dot"></div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-map-icon',
        html: iconHtml,
        iconSize: [38, 48],
        iconAnchor: [19, 46],
        popupAnchor: [0, -42]
      });

      const popupContent = `
        <div class="map-popup-card">
          <div class="popup-header request">
            <span class="popup-tag urgent">EMERGENCY NEEDED LOCATION</span>
            <span class="popup-status ${req.Status.toLowerCase()}">${req.Status}</span>
          </div>
          <div class="popup-body">
            <div class="popup-blood-needed">
              <span class="blood-pill-lg">${req.BloodGroupRequired}</span>
              <div>
                <strong style="font-size:1.1rem; color:#991b1b;">${req.RequiredUnits} Unit(s) Required</strong>
                <div style="font-size:0.8rem; color:#6b7280;">Patient: ${req.PatientName || 'Emergency Patient'}</div>
              </div>
            </div>
            <div class="popup-info-row">
              <span>Hospital:</span>
              <strong>${req.HospitalName || 'Regional Hospital'}</strong>
            </div>
            <div class="popup-info-row">
              <span>Location:</span>
              <span>${req.HospitalLocation || 'Downtown'}</span>
            </div>
            <div class="popup-info-row">
              <span>Target Blood Bank:</span>
              <span>${req.BloodBankName || 'City Blood Bank'}</span>
            </div>
            <div class="popup-info-row">
              <span>Requested:</span>
              <span>${req.RequestDate ? new Date(req.RequestDate).toLocaleDateString() : 'Active'}</span>
            </div>
          </div>
          <div class="popup-actions">
            <button id="btn-match-req-${req.RequestID}" class="popup-btn primary">
              Find Compatible Donors
            </button>
          </div>
        </div>
      `;

      const marker = L.marker([req.lat, req.lng], { icon: customIcon }).bindPopup(popupContent, {
        maxWidth: 320,
        className: 'custom-leaflet-popup'
      });

      marker.on('popupopen', () => {
        const btn = document.getElementById(`btn-match-req-${req.RequestID}`);
        if (btn) {
          btn.onclick = () => {
            setSelectedRequest(req);
            map.closePopup();
          };
        }
      });

      marker.on('click', () => {
        setSelectedRequest(req);
      });

      marker.addTo(markersLayer);
      bounds.extend([req.lat, req.lng]);
      hasPoints = true;
    });

    // B) Render Donors (Green / Blood Group Badges)
    filteredDonors.forEach(donor => {
      const isEligible = donor.IsActive !== false;
      const isUniversal = donor.BloodGroup === 'O-';

      const iconHtml = `
        <div class="map-marker-pin donor ${isUniversal ? 'universal' : ''}" title="Donor: ${donor.DonorName} (${donor.BloodGroup})">
          <div class="pin-badge bg-green">${donor.BloodGroup}</div>
          <div class="pin-icon donor-dot"></div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-map-icon',
        html: iconHtml,
        iconSize: [36, 44],
        iconAnchor: [18, 42],
        popupAnchor: [0, -38]
      });

      const popupContent = `
        <div class="map-popup-card">
          <div class="popup-header donor">
            <span class="popup-tag donor">REGISTERED DONOR</span>
            <span class="popup-status ${isEligible ? 'eligible' : 'cooldown'}">${isEligible ? 'Active Donor' : 'Cooldown'}</span>
          </div>
          <div class="popup-body">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
              <span class="blood-pill-lg green">${donor.BloodGroup}</span>
              <div>
                <strong style="font-size:1.1rem; color:#111827;">${donor.DonorName}</strong>
                <div style="font-size:0.8rem; color:#6b7280;">Age ${donor.Age || 28} • ${donor.Gender === 'F' ? 'Female' : donor.Gender === 'M' ? 'Male' : 'Donor'}</div>
              </div>
            </div>
            <div class="popup-info-row">
              <span>Address:</span>
              <span>${donor.Address || 'City Center'}</span>
            </div>
            <div class="popup-info-row">
              <span>Contact:</span>
              <strong>${donor.ContactNo || 'N/A'}</strong>
            </div>
            <div class="popup-info-row">
              <span>Total Donations:</span>
              <span>${donor.TotalDonations || 0} times</span>
            </div>
            <div class="popup-info-row">
              <span>Last Donation:</span>
              <span>${donor.LastDonationDate || 'First time donor'}</span>
            </div>
          </div>
          <div class="popup-actions">
            ${donor.ContactNo ? `
              <a href="tel:${donor.ContactNo}" class="popup-btn secondary" style="text-decoration:none; text-align:center;">
                Contact Donor
              </a>
            ` : ''}
          </div>
        </div>
      `;

      const marker = L.marker([donor.lat, donor.lng], { icon: customIcon }).bindPopup(popupContent, {
        maxWidth: 300,
        className: 'custom-leaflet-popup'
      });

      marker.addTo(markersLayer);
      bounds.extend([donor.lat, donor.lng]);
      hasPoints = true;
    });

    // C) Render Blood Banks (Sapphire Storage Depots)
    filteredBloodBanks.forEach(bank => {
      const iconHtml = `
        <div class="map-marker-pin bloodbank" title="Blood Bank: ${bank.BloodBankName}">
          <div class="pin-badge bg-blue">DEPOT</div>
          <div class="pin-icon bank-dot"></div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-map-icon',
        html: iconHtml,
        iconSize: [36, 44],
        iconAnchor: [18, 42],
        popupAnchor: [0, -38]
      });

      const popupContent = `
        <div class="map-popup-card">
          <div class="popup-header bank">
            <span class="popup-tag bank">AUTHORIZED BLOOD REPOSITORY</span>
          </div>
          <div class="popup-body">
            <strong style="font-size:1.1rem; color:#1e40af; display:block; margin-bottom:6px;">${bank.BloodBankName}</strong>
            <div class="popup-info-row">
              <span>Location:</span>
              <span>${bank.Location}</span>
            </div>
            <div class="popup-info-row">
              <span>📞 Contact:</span>
              <span>${bank.ContactNo}</span>
            </div>
            <div class="popup-info-row">
              <span>📦 Storage Capacity:</span>
              <strong>${bank.Capacity || 1000} Units</strong>
            </div>
          </div>
        </div>
      `;

      const marker = L.marker([bank.lat, bank.lng], { icon: customIcon }).bindPopup(popupContent, {
        maxWidth: 300,
        className: 'custom-leaflet-popup'
      });

      marker.addTo(markersLayer);
      bounds.extend([bank.lat, bank.lng]);
      hasPoints = true;
    });

    // Fit map bounds if points exist
    if (hasPoints && !selectedRequest) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
  }, [filteredRequests, filteredDonors, filteredBloodBanks, selectedRequest]);

  // 3. Render Compatibility Connector Routes when an Emergency Request is selected
  useEffect(() => {
    if (!mapInstanceRef.current || !routesLayerRef.current) return;

    const map = mapInstanceRef.current;
    const routesLayer = routesLayerRef.current;
    routesLayer.clearLayers();

    if (!selectedRequest) return;

    const bounds = L.latLngBounds();
    bounds.extend([selectedRequest.lat, selectedRequest.lng]);

    // Draw pulsating center radius circle around the emergency location
    L.circle([selectedRequest.lat, selectedRequest.lng], {
      radius: 8000, // 8 km radius
      color: '#dc2626',
      fillColor: '#fee2e2',
      fillOpacity: 0.15,
      weight: 1.5,
      dashArray: '6, 6'
    }).addTo(routesLayer);

    // Draw connector lines to top 8 closest compatible donors
    const topMatches = compatibleDonorsForSelected.slice(0, 8);

    topMatches.forEach((donor, idx) => {
      const latlngs = [
        [selectedRequest.lat, selectedRequest.lng],
        [donor.lat, donor.lng]
      ];

      // Polyline with distance styling
      L.polyline(latlngs, {
        color: idx === 0 ? '#16a34a' : '#2563eb',
        weight: idx === 0 ? 3.5 : 2,
        opacity: 0.8,
        dashArray: '4, 6'
      }).addTo(routesLayer);

      // Distance Tooltip at midpoint
      const midLat = (selectedRequest.lat + donor.lat) / 2;
      const midLng = (selectedRequest.lng + donor.lng) / 2;

      const distanceIcon = L.divIcon({
        className: 'distance-tooltip-icon',
        html: `<div class="dist-pill ${idx === 0 ? 'fastest' : ''}">${donor.distance} km (~${donor.travelMinutes}m)</div>`,
        iconSize: [80, 20],
        iconAnchor: [40, 10]
      });

      L.marker([midLat, midLng], { icon: distanceIcon, interactive: false }).addTo(routesLayer);

      bounds.extend([donor.lat, donor.lng]);
    });

    map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
  }, [selectedRequest, compatibleDonorsForSelected]);

  // 4. Handle GPS "Locate Me"
  const handleLocateUser = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      pos => {
        setIsLocating(false);
        const { latitude, longitude } = pos.coords;

        if (mapInstanceRef.current) {
          const map = mapInstanceRef.current;
          map.flyTo([latitude, longitude], 14, { duration: 1.5 });

          if (userMarkerRef.current) {
            userMarkerRef.current.remove();
          }

          const userIcon = L.divIcon({
            className: 'user-gps-marker',
            html: `<div class="user-pulse-dot"></div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          });

          userMarkerRef.current = L.marker([latitude, longitude], { icon: userIcon })
            .bindPopup('<strong>📍 Your Current Location</strong>')
            .addTo(map)
            .openPopup();
        }
      },
      err => {
        setIsLocating(false);
        console.warn('Geolocation error:', err.message);
        // Fallback to default metropolitan coordinates
        if (mapInstanceRef.current) {
          mapInstanceRef.current.flyTo([BASE_LAT, BASE_LNG], 13);
        }
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const handleResetView = () => {
    setSelectedRequest(null);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([BASE_LAT, BASE_LNG], 12, { duration: 1 });
    }
  };

  return (
    <div className="live-map-wrapper">
      {/* Map Header & Summary Statistics */}
      <div className="map-summary-bar">
        <div className="map-stat-card">
          <div className="stat-icon-wrap red">
            <AlertTriangle size={20} />
          </div>
          <div>
            <div className="stat-val">{geocodedRequests.filter(r => r.Status === 'Pending').length}</div>
            <div className="stat-lbl">Active Emergency Needs</div>
          </div>
        </div>

        <div className="map-stat-card">
          <div className="stat-icon-wrap green">
            <Heart size={20} />
          </div>
          <div>
            <div className="stat-val">{geocodedDonors.length}</div>
            <div className="stat-lbl">Registered Donors Mapped</div>
          </div>
        </div>

        <div className="map-stat-card">
          <div className="stat-icon-wrap blue">
            <Building2 size={20} />
          </div>
          <div>
            <div className="stat-val">{geocodedBloodBanks.length}</div>
            <div className="stat-lbl">Blood Centers & Depots</div>
          </div>
        </div>

        <div className="map-stat-card">
          <div className="stat-icon-wrap purple">
            <Zap size={20} />
          </div>
          <div>
            <div className="stat-val">{geocodedDonors.filter(d => d.BloodGroup === 'O-').length}</div>
            <div className="stat-lbl">Universal O- Donors</div>
          </div>
        </div>
      </div>

      {/* Control & Filter Toolbar */}
      <div className="map-toolbar">
        {/* Layer Selector */}
        <div className="toolbar-group">
          <label className="toolbar-label">
            <Layers size={14} /> Layer
          </label>
          <div className="pill-selector">
            <button
              className={`pill-btn ${selectedLayer === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedLayer('all')}
            >
              All Network
            </button>
            <button
              className={`pill-btn red ${selectedLayer === 'requests' ? 'active' : ''}`}
              onClick={() => setSelectedLayer('requests')}
            >
              Needed Requests ({geocodedRequests.length})
            </button>
            <button
              className={`pill-btn green ${selectedLayer === 'donors' ? 'active' : ''}`}
              onClick={() => setSelectedLayer('donors')}
            >
              Donors ({geocodedDonors.length})
            </button>
            <button
              className={`pill-btn blue ${selectedLayer === 'bloodbanks' ? 'active' : ''}`}
              onClick={() => setSelectedLayer('bloodbanks')}
            >
              Banks ({geocodedBloodBanks.length})
            </button>
          </div>
        </div>

        {/* Blood Group Filter */}
        <div className="toolbar-group">
          <label className="toolbar-label">
            <Filter size={14} /> Blood Type
          </label>
          <select
            value={selectedBloodGroup}
            onChange={e => setSelectedBloodGroup(e.target.value)}
            className="map-select"
          >
            <option value="ALL">All Blood Types</option>
            {['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'].map(bg => (
              <option key={bg} value={bg}>
                {bg} {bg === 'O-' ? '(Universal Donor)' : bg === 'AB+' ? '(Universal Recipient)' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter for Requests */}
        <div className="toolbar-group">
          <label className="toolbar-label">
            <Activity size={14} /> Status
          </label>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="map-select"
          >
            <option value="all">All Requests</option>
            <option value="pending">Pending Emergency Only</option>
          </select>
        </div>

        {/* Quick Search */}
        <div className="toolbar-group search-group" style={{ flex: 1 }}>
          <label className="toolbar-label">
            <Search size={14} /> Quick Search
          </label>
          <div className="search-input-wrap">
            <input
              type="text"
              placeholder="Search donor name, hospital, location..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="map-search-input"
            />
            {searchQuery && (
              <button className="search-clear-btn" onClick={() => setSearchQuery('')}>
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Quick Actions (GPS / Reset) */}
        <div className="toolbar-group actions-group">
          <label className="toolbar-label">&nbsp;</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="map-action-btn"
              onClick={handleLocateUser}
              title="Locate my position"
              disabled={isLocating}
            >
              <Crosshair size={16} /> {isLocating ? 'Locating...' : 'My Location'}
            </button>
            <button
              className="map-action-btn secondary"
              onClick={handleResetView}
              title="Reset Zoom and Center"
            >
              <Compass size={16} /> Reset
            </button>
          </div>
        </div>
      </div>

      {/* Main Map & Live Compatibility Panel Grid */}
      <div className="map-main-grid">
        {/* Leaflet Map Canvas Container */}
        <div className="map-canvas-container">
          <div ref={mapContainerRef} className="leaflet-map-canvas" />

          {/* Map Legend Overlay */}
          <div className="map-legend-box">
            <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#374151', marginBottom: '6px' }}>
              MAP LEGEND
            </div>
            <div className="legend-item">
              <span className="legend-pin red"></span>
              <span>Needed Location (Hospital Request)</span>
            </div>
            <div className="legend-item">
              <span className="legend-pin green"></span>
              <span>Registered Blood Donor</span>
            </div>
            <div className="legend-item">
              <span className="legend-pin blue"></span>
              <span>Blood Bank / Storage Depot</span>
            </div>
            <div className="legend-item">
              <span className="legend-line green"></span>
              <span>Compatible Proximity Route</span>
            </div>
          </div>
        </div>

        {/* Interactive Compatibility & Match Drawer */}
        <div className="map-side-panel">
          <div className="side-panel-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Zap size={18} color="#dc2626" />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#111827' }}>
                Emergency Match Engine
              </h3>
            </div>
            {selectedRequest && (
              <button
                className="btn-clear-match"
                onClick={() => setSelectedRequest(null)}
                title="Clear selected request"
              >
                Clear Selection
              </button>
            )}
          </div>

          {!selectedRequest ? (
            <div className="side-panel-empty">
              <strong style={{ color: '#374151', display: 'block', marginBottom: '6px', fontSize: '1.05rem' }}>
                Click any Needed Location pin on the map
              </strong>
              <p style={{ color: '#6b7280', fontSize: '0.85rem', margin: 0 }}>
                Select an Emergency Blood Request to automatically trace proximity routes and discover nearby compatible donors.
              </p>

              {/* Quick Select from Active Pending Requests */}
              <div style={{ marginTop: '20px', textAlign: 'left', width: '100%' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#991b1b', marginBottom: '8px' }}>
                  Active Emergency Requests ({geocodedRequests.filter(r => r.Status === 'Pending').length})
                </div>
                <div className="side-requests-list">
                  {geocodedRequests
                    .filter(r => r.Status === 'Pending')
                    .slice(0, 5)
                    .map(req => (
                      <div
                        key={req.RequestID}
                        className="side-req-item"
                        onClick={() => {
                          setSelectedRequest(req);
                          if (mapInstanceRef.current) {
                            mapInstanceRef.current.flyTo([req.lat, req.lng], 13, { duration: 1 });
                          }
                        }}
                      >
                        <span className="req-blood-pill">{req.BloodGroupRequired}</span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <strong style={{ fontSize: '0.88rem', color: '#1f2937', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {req.HospitalName}
                          </strong>
                          <span style={{ fontSize: '0.78rem', color: '#6b7280' }}>
                            {req.RequiredUnits} Unit(s) • {req.PatientName}
                          </span>
                        </div>
                        <span className="btn-inspect-arrow">➔</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="side-panel-content">
              {/* Selected Request Details Card */}
              <div className="selected-req-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <span className="req-blood-pill-lg">{selectedRequest.BloodGroupRequired}</span>
                  <span className="badge-urgent">URGENT REQUIREMENT</span>
                </div>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '1rem', color: '#111827' }}>
                  {selectedRequest.HospitalName}
                </h4>
                <div style={{ fontSize: '0.82rem', color: '#4b5563', marginBottom: '4px' }}>
                  📍 {selectedRequest.HospitalLocation || 'Downtown'}
                </div>
                <div style={{ fontSize: '0.82rem', color: '#6b7280' }}>
                  Patient: <strong>{selectedRequest.PatientName}</strong> • {selectedRequest.RequiredUnits} Unit(s) needed
                </div>
              </div>

              {/* Matched Donors Header */}
              <div className="matched-header">
                <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#166534' }}>
                  🎯 {compatibleDonorsForSelected.length} Compatible Donors Found
                </span>
                <small style={{ color: '#6b7280' }}>Sorted by closest distance</small>
              </div>

              {/* List of Matched Donors */}
              <div className="matched-donors-list">
                {compatibleDonorsForSelected.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af', fontSize: '0.88rem' }}>
                    No compatible donors registered in this area yet.
                  </div>
                ) : (
                  compatibleDonorsForSelected.map((donor, idx) => (
                    <div key={donor.DonorID} className={`matched-donor-card ${idx === 0 ? 'closest' : ''}`}>
                      {idx === 0 && <div className="closest-ribbon">⚡ CLOSEST MATCH</div>}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className="donor-blood-badge">{donor.BloodGroup}</span>
                          <strong style={{ fontSize: '0.92rem', color: '#111827' }}>{donor.DonorName}</strong>
                        </div>
                        <div className="distance-badge">
                          <strong>{donor.distance} km</strong>
                          <span>~{donor.travelMinutes} mins</span>
                        </div>
                      </div>

                      <div style={{ fontSize: '0.8rem', color: '#4b5563', marginBottom: '8px' }}>
                        📍 {donor.Address || 'City Center'} • {donor.TotalDonations || 0} donations
                      </div>

                      <div style={{ display: 'flex', gap: '6px' }}>
                        {donor.ContactNo && (
                          <a
                            href={`tel:${donor.ContactNo}`}
                            className="btn-match-action call"
                            title="Call donor"
                          >
                            <Phone size={13} /> {donor.ContactNo}
                          </a>
                        )}
                        <button
                          className="btn-match-action center"
                          onClick={() => {
                            if (mapInstanceRef.current) {
                              mapInstanceRef.current.flyTo([donor.lat, donor.lng], 15, { duration: 1 });
                            }
                          }}
                          title="Zoom to donor on map"
                        >
                          <Navigation size={13} /> View on Map
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LiveNetworkMap;

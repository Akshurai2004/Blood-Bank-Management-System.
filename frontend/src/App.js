import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Heart, Users, Building2, Droplet, AlertCircle, Shield, LogIn, LogOut, Award, RefreshCw } from 'lucide-react';
import LiveNetworkMap from './LiveNetworkMap';
import 'leaflet/dist/leaflet.css';

const getApiBase = () => {
  const envUrl = (process.env.REACT_APP_API_URL || '').trim();
  if (envUrl) {
    let clean = envUrl.replace(/\/+$/, '');
    // If base URL was provided without '/api' suffix (e.g. https://xxx.onrender.com), append '/api'
    if (!clean.endsWith('/api')) {
      clean = clean + '/api';
    }
    return clean;
  }
  return process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000/api';
};

const API_BASE = getApiBase();

const buildApiUrl = (path) => {
  let cleanPath = (path || '').trim();
  if (!cleanPath.startsWith('/')) {
    cleanPath = '/' + cleanPath;
  }
  // Prevent duplicate /api/ if path already has /api prefix
  if (API_BASE.endsWith('/api') && cleanPath.startsWith('/api/')) {
    cleanPath = cleanPath.substring(4);
  }
  return `${API_BASE}${cleanPath}`;
};



const BloodBankManagement = () => {
  // Donor search state and handler
  const [donorSearch, setDonorSearch] = useState('');
  const [donorSearchResult, setDonorSearchResult] = useState(null); // stores the matched donor's ID
  const [donorSearchMessage, setDonorSearchMessage] = useState('');
  function handleDonorSearch(e) {
    const value = e.target.value;
    setDonorSearch(value);
    setDonorSearchMessage('');
    if (!value.trim()) {
      setDonorSearchResult(null);
      return;
    }
    // Search by ID (number), name (case-insensitive), or blood group (case-insensitive)
    const lower = value.trim().toLowerCase();
    let found = null;
    found = donors.find(d =>
      String(d.DonorID) === value.trim() ||
      (d.DonorName && d.DonorName.toLowerCase().includes(lower)) ||
      (d.BloodGroup && d.BloodGroup.toLowerCase() === lower)
    );
    if (found) {
      setDonorSearchResult(found.DonorID);
    } else {
      setDonorSearchResult(null);
      setDonorSearchMessage('No donor found matching your search criteria.');
    }
  }
    // Patient search state and handler
  const [patientSearch, setPatientSearch] = useState('');
  const [patientSearchResult, setPatientSearchResult] = useState(null); // stores the matched patient ID
  const [patientSearchMessage, setPatientSearchMessage] = useState('');
  function handlePatientSearch(e) {
    const value = e.target.value;
    setPatientSearch(value);
    setPatientSearchMessage('');
    if (!value.trim()) {
      setPatientSearchResult(null);
      return;
    }
    const lower = value.trim().toLowerCase();
    let found = null;
    found = patients.find(p =>
      String(p.PatientID) === value.trim() ||
      (p.PatientName && p.PatientName.toLowerCase().includes(lower)) ||
      (p.BloodGroupRequired && p.BloodGroupRequired.toLowerCase() === lower)
    );
    if (found) {
      setPatientSearchResult(found.PatientID);
    } else {
      setPatientSearchResult(null);
      setPatientSearchMessage('No patient found matching your search criteria.');
    }
  }

  // For editing patient
  const [editPatientId, setEditPatientId] = useState(null);
  const [editPatientForm, setEditPatientForm] = useState({
    name: '', age: '', gender: 'M', blood_group: 'A+', hospital_id: '', contact: '', condition: ''
  });
  const [showEditPatientModal, setShowEditPatientModal] = useState(false);
  // For delete confirmation
  const [deletePatientId, setDeletePatientId] = useState(null);
  const [showDeletePatientModal, setShowDeletePatientModal] = useState(false);

  function openEditPatientModal(patient) {
    setEditPatientId(patient.PatientID);
    setEditPatientForm({
      name: patient.PatientName || '',
      age: patient.Age ? String(patient.Age) : '',
      gender: patient.Gender || 'M',
      blood_group: patient.BloodGroupRequired || 'A+',
      hospital_id: patient.HospitalID ? String(patient.HospitalID) : '',
      contact: patient.ContactNo || '',
      condition: patient.MedicalCondition || ''
    });
    setShowEditPatientModal(true);
  }

  function closeEditPatientModal() {
    setShowEditPatientModal(false);
    setEditPatientId(null);
  }

  async function handleEditPatientSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request(`/patients/${editPatientId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          PatientName: editPatientForm.name,
          Age: parseInt(editPatientForm.age, 10),
          Gender: editPatientForm.gender,
          BloodGroupRequired: editPatientForm.blood_group,
          HospitalID: parseInt(editPatientForm.hospital_id, 10),
          ContactNo: editPatientForm.contact,
          MedicalCondition: editPatientForm.condition
        })
      });
      if (data.success) {
        showMessage('Patient updated successfully!', 'success');
        closeEditPatientModal();

        // Optimistically update local patients state so the table reflects the
        // edited values immediately (useful if the backend response doesn't
        // return the full updated row). We'll still refresh from server for
        // consistency.
        const hospitalId = parseInt(editPatientForm.hospital_id, 10) || null;
        const hospital = hospitals.find(h => Number(h.HospitalID) === hospitalId);

        setPatients(prev => prev.map(p => {
          if (p.PatientID === editPatientId) {
            return {
              ...p,
              PatientName: editPatientForm.name,
              Age: Number(editPatientForm.age) || p.Age,
              Gender: editPatientForm.gender,
              BloodGroupRequired: editPatientForm.blood_group,
              HospitalID: hospitalId,
              HospitalName: hospital ? hospital.HospitalName : p.HospitalName,
              ContactNo: editPatientForm.contact,
              MedicalCondition: editPatientForm.condition
            };
          }
          return p;
        }));

        // Refresh from server to ensure canonical state (await so UI shows updated data immediately)
        await fetchPatients();
      } else {
        showMessage(data.detail || 'Error updating patient', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error updating patient');
    } finally {
      setLoading(false);
    }
  }

  function openDeletePatientModal(patientId) {
    setDeletePatientId(patientId);
    setShowDeletePatientModal(true);
  }

  function closeDeletePatientModal() {
    setShowDeletePatientModal(false);
    setDeletePatientId(null);
  }

  async function handleDeletePatient() {
    setLoading(true);
    try {
      const data = await request(`/patients/${deletePatientId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      if (data.success) {
        showMessage('Patient deleted successfully!', 'success');
        closeDeletePatientModal();
        fetchPatients();
      } else {
        showMessage(data.detail || 'Error deleting patient', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error deleting patient');
    } finally {
      setLoading(false);
    }
  }

  const [auth, setAuth] = useState(() => {
    try {
      const saved = localStorage.getItem('bb_auth');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [loginMethod, setLoginMethod] = useState('password'); // 'password' | 'otp'
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [loginOtp, setLoginOtp] = useState('');
  const [loginOtpSent, setLoginOtpSent] = useState(false);

  const [registerForm, setRegisterForm] = useState({
    full_name: '', email: '', password: '', role: 'Donor', age: '', gender: 'M', blood_group: 'A+', contact: '', address: '', hospital_id: '', blood_bank_id: ''
  });
  const [registerStep, setRegisterStep] = useState('form'); // 'form' | 'otp'
  const [registerOtp, setRegisterOtp] = useState('');
  const [otpTimer, setOtpTimer] = useState(0);

  const [donorPortalData, setDonorPortalData] = useState({
    donor: null, eligibility: '', donation_history: [], bloodbanks: []
  });
  const [donorPortalLoading, setDonorPortalLoading] = useState(false);
  const [queueStatus, setQueueStatus] = useState(null);
  const [recentBroadcasts, setRecentBroadcasts] = useState([]);

  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('bb_auth');
    if (saved) {
      try {
        const u = JSON.parse(saved)?.user;
        if (u?.role === 'Donor') return 'donor-portal';
        if (u?.role === 'Hospital') return 'requests';
      } catch (e) {}
    }
    return 'dashboard';
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success' or 'error'
  const messageTimerRef = useRef(null);

  const [donors, setDonors] = useState([]);
  const [bloodBanks, setBloodBanks] = useState([]);
  const [hospitals, setHospitals] = useState([]);
  const [patients, setPatients] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [requests, setRequests] = useState([]);
  const [allocations, setAllocations] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [bloodUnits, setBloodUnits] = useState([]);

  const [donorForm, setDonorForm] = useState({
    name: '', age: '', gender: 'M', blood_group: 'A+', contact: '', email: '', address: ''
  });
  // For editing donor
  const [editDonorId, setEditDonorId] = useState(null);
  const [editDonorForm, setEditDonorForm] = useState({
    name: '', age: '', gender: 'M', blood_group: 'A+', contact: '', email: '', address: ''
  });
  const [showEditModal, setShowEditModal] = useState(false);
  // For delete confirmation
  const [deleteDonorId, setDeleteDonorId] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  // Edit Donor Handlers
  function openEditDonorModal(donor) {
    setEditDonorId(donor.DonorID);
    setEditDonorForm({
      name: donor.DonorName || '',
      age: donor.Age ? String(donor.Age) : '',
      gender: donor.Gender || 'M',
      blood_group: donor.BloodGroup || 'A+',
      contact: donor.ContactNo || '',
      email: donor.Email || '',
      address: donor.Address || ''
    });
    setShowEditModal(true);
  }

  function closeEditDonorModal() {
    setShowEditModal(false);
    setEditDonorId(null);
  }

  async function handleEditDonorSubmit(e) {
    e.preventDefault();
    const age = parseInt(editDonorForm.age, 10);
    if (age < 18 || age > 65) {
      showMessage('Age must be between 18 and 65.', 'error');
      return;
    }
    if (editDonorForm.contact.length !== 10) {
      showMessage('Contact number must be exactly 10 digits.', 'error');
      return;
    }
    if (!/^\d{10}$/.test(editDonorForm.contact)) {
      showMessage('Contact number must contain only digits.', 'error');
      return;
    }
    if (editDonorForm.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(editDonorForm.email)) {
        showMessage('Please enter a valid email address.', 'error');
        return;
      }
    }
    setLoading(true);
    try {
      const data = await request(`/donors/${editDonorId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          DonorName: editDonorForm.name,
          Age: age,
          Gender: editDonorForm.gender,
          BloodGroup: editDonorForm.blood_group,
          ContactNo: editDonorForm.contact,
          Email: editDonorForm.email,
          Address: editDonorForm.address
        })
      });
      if (data.success) {
        showMessage('Donor updated successfully!', 'success');
        closeEditDonorModal();
        // Small delay to ensure DB transaction is committed
        await new Promise(resolve => setTimeout(resolve, 100));
        await fetchDonors();
        await fetchStatistics();
      } else {
        showMessage(data.detail || 'Error updating donor', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error updating donor');
    } finally {
      setLoading(false);
    }
  }

  // Delete Donor Handlers
  function openDeleteDonorModal(donorId) {
    setDeleteDonorId(donorId);
    setShowDeleteModal(true);
  }

  function closeDeleteDonorModal() {
    setShowDeleteModal(false);
    setDeleteDonorId(null);
  }

  async function handleDeleteDonor() {
    setLoading(true);
    try {
      const data = await request(`/donors/${deleteDonorId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      if (data.success) {
        showMessage('Donor deleted successfully!', 'success');
        closeDeleteDonorModal();
        fetchDonors();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error deleting donor', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error deleting donor');
    } finally {
      setLoading(false);
    }
  }
  const [patientForm, setPatientForm] = useState({
    name: '', age: '', gender: 'M', blood_group: 'A+', hospital_id: '', contact: '', condition: ''
  });
  const [requestForm, setRequestForm] = useState({
    patient_id: '', blood_bank_id: '', required_units: ''
  });
  // For editing a request
  const [editRequestId, setEditRequestId] = useState(null);
  const [editRequestForm, setEditRequestForm] = useState({ patient_id: '', blood_bank_id: '', required_units: '' });
  const [showEditRequestModal, setShowEditRequestModal] = useState(false);
  // For delete confirmation of a request
  const [deleteRequestId, setDeleteRequestId] = useState(null);
  const [showDeleteRequestModal, setShowDeleteRequestModal] = useState(false);
  const [donationForm, setDonationForm] = useState({
    donor_id: '', blood_bank_id: '', component: 'Whole Blood', quantity: ''
  });
  const [hospitalForm, setHospitalForm] = useState({
    name: '', location: '', contact: '', email: ''
  });
  const [bloodBankForm, setBloodBankForm] = useState({
    name: '', location: '', contact: '', capacity: ''
  });
  const [allocationForm, setAllocationForm] = useState({
    request_id: '', unit_id: ''
  });

  const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
  const components = ['Whole Blood', 'RBC', 'Plasma', 'Platelets'];
  const genders = ['M', 'F', 'O'];

  const showMessage = (msg, type) => {
    if (messageTimerRef.current) {
      clearTimeout(messageTimerRef.current);
    }
    setMessage(msg);
    setMessageType(type);
    messageTimerRef.current = setTimeout(() => {
      setMessage('');
      setMessageType('');
    }, 3000);
  };

  const handleApiError = (error, fallbackMessage) => {
    const errMsg = error?.message || fallbackMessage;
    console.error(fallbackMessage, error);
    showMessage(errMsg, 'error');
  };

  const saveAuth = (authData) => {
    setAuth(authData);
    if (authData) {
      localStorage.setItem('bb_auth', JSON.stringify(authData));
    } else {
      localStorage.removeItem('bb_auth');
    }
  };

  // Countdown timer for OTP resend cooldown
  useEffect(() => {
    let interval = null;
    if (otpTimer > 0) {
      interval = setInterval(() => {
        setOtpTimer(prev => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [otpTimer]);

  const handleLoginSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const res = await request('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: loginForm.email.trim(),
          password: loginForm.password
        })
      });
      if (res.success) {
        saveAuth(res);
        loadAllData();
        showMessage(`Welcome back, ${res.user.name}!`, 'success');
        setShowAuthModal(false);
        if (res.user.role === 'Donor') {
          setActiveTab('donor-portal');
        } else if (res.user.role === 'Hospital') {
          setActiveTab('requests');
        } else {
          setActiveTab('dashboard');
        }
      }
    } catch (err) {
      handleApiError(err, 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSendLoginOTP = async (e) => {
    if (e) e.preventDefault();
    const cleanEmail = loginForm.email.trim();
    if (!cleanEmail) {
      showMessage('Please enter your email address.', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await request('/auth/send-login-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: cleanEmail })
      });
      if (res.success) {
        setLoginOtpSent(true);
        setLoginOtp('');
        setOtpTimer(60);
        showMessage(`Verification code sent to ${cleanEmail}! Please check your email.`, 'success');
      }
    } catch (err) {
      handleApiError(err, 'Failed to send login code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyLoginOTP = async (e) => {
    if (e) e.preventDefault();
    const cleanOtp = loginOtp.trim();
    if (!cleanOtp || cleanOtp.length !== 6) {
      showMessage('Please enter the 6-digit verification code sent to your email.', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await request('/auth/verify-login-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: loginForm.email.trim(),
          otp: cleanOtp
        })
      });
      if (res.success) {
        saveAuth(res);
        loadAllData();
        showMessage(`Welcome back, ${res.user.name}!`, 'success');
        setShowAuthModal(false);
        setLoginOtpSent(false);
        setLoginOtp('');
        if (res.user.role === 'Donor') {
          setActiveTab('donor-portal');
        } else if (res.user.role === 'Hospital') {
          setActiveTab('requests');
        } else {
          setActiveTab('dashboard');
        }
      }
    } catch (err) {
      handleApiError(err, 'OTP verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResendLoginOTP = async () => {
    if (otpTimer > 0) return;
    setLoading(true);
    try {
      const res = await request('/auth/resend-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginForm.email.trim(), purpose: 'login' })
      });
      if (res.success) {
        setLoginOtp('');
        setOtpTimer(60);
        showMessage(`New verification code sent to ${loginForm.email.trim()}! Please check your email.`, 'success');
      }
    } catch (err) {
      handleApiError(err, 'Failed to resend code');
    } finally {
      setLoading(false);
    }
  };

  const handleSendRegisterOTP = async (e) => {
    if (e) e.preventDefault();
    
    // Client-side validations
    if (!registerForm.full_name || registerForm.full_name.trim().length < 2) {
      showMessage('Please enter your full name.', 'error');
      return;
    }
    if (!registerForm.email || !registerForm.email.includes('@')) {
      showMessage('Please enter a valid email address.', 'error');
      return;
    }
    if (!registerForm.password || registerForm.password.length < 6) {
      showMessage('Password must be at least 6 characters.', 'error');
      return;
    }

    if (registerForm.role === 'Donor') {
      if (registerForm.age && (parseInt(registerForm.age, 10) < 18 || parseInt(registerForm.age, 10) > 65)) {
        showMessage('Donor age must be between 18 and 65 years.', 'error');
        return;
      }
      if (registerForm.contact && registerForm.contact.replace(/\D/g, '').length !== 10) {
        showMessage('Contact number must be exactly 10 digits.', 'error');
        return;
      }
    }

    setLoading(true);
    try {
      const payload = {
        full_name: registerForm.full_name.trim(),
        email: registerForm.email.trim().toLowerCase(),
        password: registerForm.password,
        role: registerForm.role
      };

      if (registerForm.role === 'Donor') {
        if (registerForm.age) {
          payload.age = parseInt(registerForm.age, 10);
        }
        if (registerForm.gender) payload.gender = registerForm.gender;
        if (registerForm.blood_group) payload.blood_group = registerForm.blood_group;
        if (registerForm.contact && registerForm.contact.trim()) payload.contact = registerForm.contact.trim();
        if (registerForm.address && registerForm.address.trim()) payload.address = registerForm.address.trim();
      }
      if (registerForm.role === 'Hospital' && registerForm.hospital_id) {
        payload.hospital_id = parseInt(registerForm.hospital_id, 10);
      }
      if (registerForm.role === 'Admin' && registerForm.blood_bank_id) {
        payload.blood_bank_id = parseInt(registerForm.blood_bank_id, 10);
      }

      const res = await request('/auth/send-registration-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.success) {
        setRegisterStep('otp');
        setRegisterOtp('');
        setOtpTimer(60);
        showMessage(`Verification code sent to ${registerForm.email.trim()}! Please check your email.`, 'success');
      }
    } catch (err) {
      handleApiError(err, 'Failed to send registration verification code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyRegisterOTP = async (e) => {
    if (e) e.preventDefault();
    const cleanOtp = registerOtp.trim();
    if (!cleanOtp || cleanOtp.length !== 6) {
      showMessage('Please enter the 6-digit verification code sent to your email.', 'error');
      return;
    }

    setLoading(true);
    try {
      const res = await request('/auth/verify-registration-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: registerForm.email.trim(),
          otp: cleanOtp
        })
      });

      if (res.success) {
        saveAuth(res);
        loadAllData();
        showMessage(`Account verified and registered! Welcome, ${res.user.name}!`, 'success');
        setShowAuthModal(false);
        setRegisterStep('form');
        setRegisterOtp('');
        if (res.user.role === 'Donor') {
          setActiveTab('donor-portal');
        } else if (res.user.role === 'Hospital') {
          setActiveTab('requests');
        } else {
          setActiveTab('dashboard');
        }
      }
    } catch (err) {
      handleApiError(err, 'Registration verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResendRegisterOTP = async () => {
    if (otpTimer > 0) return;
    setLoading(true);
    try {
      const res = await request('/auth/resend-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: registerForm.email.trim(),
          purpose: 'registration'
        })
      });
      if (res.success) {
        setRegisterOtp('');
        setOtpTimer(60);
        showMessage(`New registration code sent to ${registerForm.email.trim()}! Please check your email.`, 'success');
      }
    } catch (err) {
      handleApiError(err, 'Failed to resend code');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await request('/auth/logout', { method: 'POST' });
    } catch (e) {}
    saveAuth(null);
    showMessage('Logged out successfully', 'success');
    setActiveTab('dashboard');
  };

  const handleQuickDemoLogin = (email, password) => {
    setLoginForm({ email, password });
    setLoading(true);
    fetch(buildApiUrl('/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
      .then(res => res.json())
      .then(res => {
        if (res.success) {
          saveAuth(res);
          loadAllData();
          showMessage(`Logged in as ${res.user.name} (${res.user.role})`, 'success');
          setShowAuthModal(false);
          if (res.user.role === 'Donor') {
            setActiveTab('donor-portal');
          } else if (res.user.role === 'Hospital') {
            setActiveTab('requests');
          } else {
            setActiveTab('dashboard');
          }
        } else {
          showMessage(res.detail || 'Demo login failed', 'error');
        }
      })
      .catch(err => {
        handleApiError(err, 'Demo login failed');
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const fetchDonorPortal = async () => {
    const token = auth?.token || (localStorage.getItem('bb_auth') ? JSON.parse(localStorage.getItem('bb_auth')).token : null);
    if (!token) return;
    setDonorPortalLoading(true);
    try {
      const data = await request('/donor/portal-data');
      if (data.success) {
        setDonorPortalData(data);
      }
    } catch (e) {
      console.error('Error fetching donor portal data:', e);
    } finally {
      setDonorPortalLoading(false);
    }
  };

  const request = async (path, options = {}) => {
    const token = auth?.token || (localStorage.getItem('bb_auth') ? JSON.parse(localStorage.getItem('bb_auth')).token : null);
    const headers = {
      ...(options.headers || {}),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
    const response = await fetch(buildApiUrl(path), { ...options, headers });
    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      // Ignore JSON parse errors and fall back to status handling
    }

    if (!response.ok) {
      if ((response.status === 401 || response.status === 403) && !path.includes('/auth/')) {
        saveAuth(null);
        showMessage('Session expired or access denied. Please log in again.', 'error');
        setActiveTab('dashboard');
      }
      let detail = `Request failed with status ${response.status}`;
      if (typeof data?.detail === 'string') {
        detail = data.detail;
      } else if (Array.isArray(data?.detail)) {
        detail = data.detail.map(d => d.msg || JSON.stringify(d)).join(', ');
      } else if (data?.message) {
        detail = data.message;
      }
      throw new Error(detail);
    }

    return data;
  };

  const fetchQueueTelemetry = async () => {
    try {
      const res = await request('/notifications/queue-status');
      if (res.success) {
        setQueueStatus(res.telemetry);
        setRecentBroadcasts(res.telemetry?.recent_broadcasts || []);
      }
    } catch (e) {
      console.warn('Queue telemetry error:', e);
    }
  };

  async function fetchDonors() {
    try {
      const data = await request('/donors');
      if (data.success) setDonors(data.data || []);
    } catch (e) {
      console.error('Error fetching donors:', e);
    }
  }

  async function fetchBloodBanks() {
    try {
      const data = await request('/bloodbanks');
      if (data.success) setBloodBanks(data.data || []);
    } catch (e) {
      console.error('Error fetching blood banks:', e);
    }
  }

  async function fetchHospitals() {
    try {
      const data = await request('/hospitals');
      if (data.success) setHospitals(data.data || []);
    } catch (e) {
      console.error('Error fetching hospitals:', e);
    }
  }

  async function fetchPatients() {
    try {
      const data = await request('/patients');
      if (data.success) setPatients(data.data || []);
    } catch (e) {
      console.error('Error fetching patients:', e);
    }
  }

  async function fetchInventory() {
    try {
      const data = await request('/inventory');
      if (data.success) setInventory(data.data || []);
    } catch (e) {
      console.error('Error fetching inventory:', e);
    }
  }

  async function fetchRequests() {
    try {
      const data = await request('/requests');
      if (data.success) setRequests(data.data || []);
    } catch (e) {
      console.error('Error fetching requests:', e);
    }
  }

  async function fetchBloodUnits() {
    try {
      const data = await request('/bloodunits');
      if (data.success) setBloodUnits(data.data || []);
    } catch (e) {
      console.error('Error fetching blood units:', e);
    }
  }

  async function fetchAllocations() {
    try {
      const data = await request('/allocations');
      if (data.success) setAllocations(data.data || []);
    } catch (e) {
      console.error('Error fetching allocations:', e);
    }
  }

  async function fetchStatistics() {
    try {
      const data = await request('/statistics/dashboard');
      if (data.success) setStatistics(data.data || {});
    } catch (e) {
      console.error('Error fetching statistics:', e);
    }
  }

  const loadAllData = useCallback(async () => {
    try {
      await Promise.allSettled([
        fetchDonors(),
        fetchBloodBanks(),
        fetchHospitals(),
        fetchPatients(),
        fetchInventory(),
        fetchRequests(),
        fetchStatistics(),
        fetchBloodUnits(),
        fetchAllocations(),
        fetchQueueTelemetry()
      ]);
    } catch (error) {
      console.error('Error during data fetch:', error);
    }
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const verifySessionAndLoad = async () => {
      const stored = localStorage.getItem('bb_auth');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed?.token) {
            const res = await fetch(buildApiUrl('/auth/me'), {
              headers: { 'Authorization': `Bearer ${parsed.token}` }
            });
            if (res.ok) {
              const meData = await res.json();
              if (meData?.success && meData?.user) {
                saveAuth({ ...parsed, user: meData.user });
              }
            } else {
              console.warn('Stored token is invalid/expired. Resetting auth session.');
              saveAuth(null);
            }
          } else {
            saveAuth(null);
          }
        } catch (e) {
          saveAuth(null);
        }
      }

      await loadAllData();
    };

    verifySessionAndLoad();
  }, [loadAllData]);

  useEffect(() => {
    if (activeTab === 'donor-portal' && auth?.token) {
      fetchDonorPortal();
    }
  }, [activeTab, auth?.token]);

  useEffect(() => () => {
    if (messageTimerRef.current) {
      clearTimeout(messageTimerRef.current);
    }
  }, []);

  // Form Handlers
  async function handleAddDonor(e) {
    e.preventDefault();
    
    // Validation checks
    const age = parseInt(donorForm.age, 10);
    if (age < 18 || age > 65) {
      showMessage('Age must be between 18 and 65. People outside this age range are not allowed to donate blood.', 'error');
      return;
    }
    
    if (donorForm.contact.length !== 10) {
      showMessage('Contact number must be exactly 10 digits.', 'error');
      return;
    }
    
    if (!/^\d{10}$/.test(donorForm.contact)) {
      showMessage('Contact number must contain only digits.', 'error');
      return;
    }
    
    if (donorForm.email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(donorForm.email)) {
        showMessage('Please enter a valid email address.', 'error');
        return;
      }
    }
    
    setLoading(true);
    try {
      const data = await request('/donors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: donorForm.name,
          age: age,
          gender: donorForm.gender,
          blood_group: donorForm.blood_group,
          contact: donorForm.contact,
          email: donorForm.email,
          address: donorForm.address
        })
      });
      if (data.success) {
        showMessage('Donor added successfully!', 'success');
        setDonorForm({ name: '', age: '', gender: 'M', blood_group: 'A+', contact: '', email: '', address: '' });
        fetchDonors();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error adding donor', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error adding donor');
    } finally {
      setLoading(false);
    }
  }

  async function handleAddHospital(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request('/hospitals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: hospitalForm.name,
          location: hospitalForm.location,
          contact: hospitalForm.contact,
          email: hospitalForm.email
        })
      });
      if (data.success) {
        showMessage('Hospital added successfully!', 'success');
        setHospitalForm({ name: '', location: '', contact: '', email: '' });
        // Refresh hospitals immediately so new hospital shows up in selects
        await fetchHospitals();
      } else {
        showMessage(data.detail || 'Error adding hospital', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error adding hospital');
    } finally {
      setLoading(false);
    }
  }

  async function handleAddBloodBank(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request('/bloodbanks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: bloodBankForm.name,
          location: bloodBankForm.location,
          contact: bloodBankForm.contact,
          capacity: parseInt(bloodBankForm.capacity, 10)
        })
      });
      if (data.success) {
        showMessage('Blood bank added successfully!', 'success');
        setBloodBankForm({ name: '', location: '', contact: '', capacity: '1000' });
        fetchBloodBanks();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error adding blood bank', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error adding blood bank');
    } finally {
      setLoading(false);
    }
  }

  async function handleAddPatient(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request('/patients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: patientForm.name,
          age: parseInt(patientForm.age, 10),
          gender: patientForm.gender,
          blood_group: patientForm.blood_group,
          hospital_id: parseInt(patientForm.hospital_id, 10),
          contact: patientForm.contact,
          condition: patientForm.condition
        })
      });
      if (data.success) {
        showMessage('Patient added successfully!', 'success');
        setPatientForm({ name: '', age: '', gender: 'M', blood_group: 'A+', hospital_id: '', contact: '', condition: '' });
        fetchPatients();
      } else {
        showMessage(data.detail || 'Error adding patient', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error adding patient');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateRequest(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request('/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: parseInt(requestForm.patient_id, 10),
          blood_bank_id: parseInt(requestForm.blood_bank_id, 10),
          required_units: parseInt(requestForm.required_units, 10)
        })
      });
      if (data.success) {
        showMessage('Request created successfully!', 'success');
        setRequestForm({ patient_id: '', blood_bank_id: '', required_units: '1' });
        fetchRequests();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error creating request', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error creating request');
    } finally {
      setLoading(false);
    }
  }

  function openEditRequestModal(req) {
    // Check if the request status is Fulfilled or Denied
    if (req.Status === 'Fulfilled' || req.Status === 'Denied') {
      showMessage(
        `Cannot edit this request. The request has already been ${req.Status.toLowerCase()} and has reached its final decision.`,
        'error'
      );
      return;
    }
    
    setEditRequestId(req.RequestID);
    setEditRequestForm({
      patient_id: req.PatientID ? String(req.PatientID) : '',
      blood_bank_id: req.BloodBankID ? String(req.BloodBankID) : '',
      required_units: req.RequiredUnits ? String(req.RequiredUnits) : ''
    });
    setShowEditRequestModal(true);
  }

  function closeEditRequestModal() {
    setShowEditRequestModal(false);
    setEditRequestId(null);
  }

  async function handleEditRequestSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request(`/requests/${editRequestId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: parseInt(editRequestForm.patient_id, 10),
          blood_bank_id: parseInt(editRequestForm.blood_bank_id, 10),
          required_units: parseInt(editRequestForm.required_units, 10)
        })
      });
      if (data.success) {
        // Helpful debug info for tracing; remove or lower verbosity in production
        console.debug('PUT /requests payload:', {
          patient_id: parseInt(editRequestForm.patient_id, 10),
          blood_bank_id: parseInt(editRequestForm.blood_bank_id, 10),
          required_units: parseInt(editRequestForm.required_units, 10)
        });
        console.debug('PUT /requests response:', data);

        // Ensure the UI is refreshed from the server before closing modal so
        // the updated request shows immediately in the table and in any
        // dependent selects (e.g. Management -> pending requests list).
        await fetchRequests();

        showMessage('Request updated successfully!', 'success');
        closeEditRequestModal();
        // Do not switch tabs automatically after editing a request — keep user where they are
      } else {
        showMessage(data.detail || 'Error updating request', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error updating request');
    } finally {
      setLoading(false);
    }
  }

  function openDeleteRequestModal(req) {
    // Check if the request status is Fulfilled or Denied
    if (req.Status === 'Fulfilled' || req.Status === 'Denied') {
      showMessage(
        `Cannot delete this request. The request has already been ${req.Status.toLowerCase()} and has reached its final decision.`,
        'error'
      );
      return;
    }
    
    setDeleteRequestId(req.RequestID);
    setShowDeleteRequestModal(true);
  }

  function closeDeleteRequestModal() {
    setShowDeleteRequestModal(false);
    setDeleteRequestId(null);
  }

  async function handleDeleteRequest() {
    setLoading(true);
    try {
      const data = await request(`/requests/${deleteRequestId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' }
      });
      if (data.success) {
        showMessage('Request deleted successfully!', 'success');
        closeDeleteRequestModal();
        fetchRequests();
      } else {
        showMessage(data.detail || 'Error deleting request', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error deleting request');
    } finally {
      setLoading(false);
    }
  }

  async function handleRecordDonation(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request('/donations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          donor_id: parseInt(donationForm.donor_id, 10),
          blood_bank_id: parseInt(donationForm.blood_bank_id, 10),
          component: donationForm.component,
          quantity: parseInt(donationForm.quantity, 10)
        })
      });
      if (data.success) {
        showMessage('Donation recorded successfully!', 'success');
        setDonationForm({ donor_id: '', blood_bank_id: '', component: 'Whole Blood', quantity: '1' });
        fetchBloodUnits();
        fetchInventory();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error recording donation', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error recording donation');
    } finally {
      setLoading(false);
    }
  }

  async function handleAllocateBlood(e) {
    e.preventDefault();
    setLoading(true);
    const reqId = parseInt(allocationForm.request_id, 10);
    const unitId = allocationForm.unit_id;
    
    try {
      // Check if "No Matching Blood Type" option was selected
      if (unitId === 'no_match') {
        // Directly deny the request without allocation
        const data = await request(`/requests/${reqId}/status`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'Denied' })
        });
        
        if (data.success) {
          showMessage('Request marked as Denied due to no matching blood type available.', 'error');
          setAllocationForm({ request_id: '', unit_id: '' });
          await Promise.all([fetchRequests(), fetchStatistics()]);
        } else {
          showMessage('Failed to deny request.', 'error');
        }
      } else {
        // Normal allocation process
        const data = await request('/allocations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            request_id: reqId,
            unit_id: parseInt(unitId, 10)
          })
        });

        // Backend now handles blood type matching and status updates
        if (data.success) {
          // Blood types matched - allocation successful and request marked as Fulfilled
          showMessage(data.message || 'Blood allocated successfully and request marked as Fulfilled!', 'success');
          setAllocationForm({ request_id: '', unit_id: '' });
          await Promise.all([fetchAllocations(), fetchRequests(), fetchBloodUnits(), fetchInventory(), fetchStatistics()]);
        } else {
          // Blood types didn't match - request marked as Denied
          showMessage(data.message || 'Blood type mismatch. Request marked as Denied.', 'error');
          setAllocationForm({ request_id: '', unit_id: '' });
          await Promise.all([fetchAllocations(), fetchRequests(), fetchBloodUnits(), fetchInventory(), fetchStatistics()]);
        }
      }
    } catch (e) {
      // Handle any errors
      handleApiError(e, 'Error processing allocation');
    } finally {
      setLoading(false);
    }
  }

  // Tab Views
  function DashboardView() {
    const donorStats = statistics.donors || {};
    const bankStats = statistics.blood_banks || {};
    const requestStats = statistics.requests || {};

    return (
      <div className="dashboard-container">
        <h2 className="section-title">Dashboard</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '30px' }}>
          <div className="card" style={{ borderLeft: '4px solid #dc2626' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '5px' }}>Total Donors</div>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#991b1b' }}>{donorStats.total_donors || 0}</div>
              </div>
              <Users size={40} style={{ color: '#dc2626', opacity: 0.3 }} />
            </div>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #059669' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '5px' }}>Available Units</div>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#059669' }}>{bankStats.available_units || 0}</div>
              </div>
              <Droplet size={40} style={{ color: '#059669', opacity: 0.3 }} />
            </div>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #f59e0b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '5px' }}>Pending Requests</div>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f59e0b' }}>{requestStats.pending_requests || 0}</div>
              </div>
              <AlertCircle size={40} style={{ color: '#f59e0b', opacity: 0.3 }} />
            </div>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #3b82f6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '5px' }}>Total Hospitals</div>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>{hospitals.length}</div>
              </div>
              <Building2 size={40} style={{ color: '#3b82f6', opacity: 0.3 }} />
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Blood Group Distribution</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px' }}>
            {(donorStats.by_blood_group || []).map(bg => (
              <div key={bg.BloodGroup} style={{ padding: '10px', background: '#f3f4f6', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>{bg.BloodGroup}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#991b1b' }}>{bg.count}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const DonorsView = useMemo(() => {
    return (
      <div className="donors-container">
        <h2 className="section-title">Manage Donors</h2>

        {/* Donor Search Box */}
        <div style={{ marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input
            type="text"
            placeholder="Search donor by ID, name, or blood group..."
            value={donorSearch}
            onChange={handleDonorSearch}
            style={{ padding: '8px 12px', borderRadius: '5px', border: '1px solid #d1d5db', minWidth: '260px' }}
          />
          {donorSearchMessage && (
            <span style={{ color: '#991b1b', fontSize: '0.98rem', marginLeft: '8px' }}>{donorSearchMessage}</span>
          )}
        </div>

        {/* Add Donor Form */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Add New Donor</h3>
          <form onSubmit={handleAddDonor}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <input
                autoComplete="off"
                type="text"
                placeholder="Full Name *"
                value={donorForm.name}
                onChange={e => setDonorForm(prev => ({...prev, name: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="number"
                placeholder="Age (18-65) *"
                min="18"
                max="65"
                value={donorForm.age}
                onInput={e => {
                  e.target.value = e.target.value.replace(/[^0-9]/g, '');
                }}
                onChange={e => {
                  const value = e.target.value;
                  setDonorForm(prev => ({...prev, age: value}));
                  const numValue = parseInt(value);
                  if (value && (numValue < 18 || numValue > 65)) {
                    showMessage('Age must be between 18 and 65. People outside this age range are not allowed to donate blood.', 'error');
                  } else if (value && numValue >= 18 && numValue <= 65) {
                    setMessage('');
                    setMessageType('');
                    if (messageTimerRef.current) {
                      clearTimeout(messageTimerRef.current);
                    }
                  }
                }}
                onBlur={e => {
                  const value = e.target.value;
                  if (value && (parseInt(value) < 18 || parseInt(value) > 65)) {
                    showMessage('Age must be between 18 and 65. People outside this age range are not allowed to donate blood.', 'error');
                  }
                }}
                required
              />
              <select
                value={donorForm.gender}
                onChange={e => setDonorForm(prev => ({...prev, gender: e.target.value}))}
              >
                {genders.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
              <select
                value={donorForm.blood_group}
                onChange={e => setDonorForm(prev => ({...prev, blood_group: e.target.value}))}
              >
                {bloodGroups.map(bg => <option key={bg} value={bg}>{bg}</option>)}
              </select>
              <input
                autoComplete="off"
                type="tel"
                placeholder="Contact Number (10 digits) *"
                value={donorForm.contact}
                onChange={e => {
                  const value = e.target.value.replace(/\D/g, '');
                  if (value.length <= 10) {
                    setDonorForm(prev => ({...prev, contact: value}));
                    if (value.length === 10 || value.length < 10) {
                      setMessage('');
                      setMessageType('');
                      if (messageTimerRef.current) {
                        clearTimeout(messageTimerRef.current);
                      }
                    }
                  }
                  if (value.length > 10) {
                    showMessage('Contact number must be exactly 10 digits.', 'error');
                  }
                }}
                pattern="[0-9]{10}"
                maxLength="10"
                required
                title="Please enter exactly 10 digits"
              />
              <input
                autoComplete="off"
                type="email"
                placeholder="Email"
                value={donorForm.email}
                onChange={e => setDonorForm(prev => ({...prev, email: e.target.value}))}
                pattern="[^\s@]+@[^\s@]+\.[^\s@]+"
                title="Please enter a valid email address (e.g., example@domain.com)"
              />
            </div>
            <textarea
              autoComplete="off"
              placeholder="Address"
              value={donorForm.address}
              onChange={e => setDonorForm(prev => ({...prev, address: e.target.value}))}
              style={{ marginTop: '10px' }}
            />
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Adding...' : 'Add Donor'}
            </button>
          </form>
        </div>

        {/* Edit Donor Modal */}
        {showEditModal && (
          <div className="modal-overlay" style={{ position: 'fixed', top:0, left:0, width:'100vw', height:'100vh', background:'rgba(0,0,0,0.3)', zIndex:2000, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div className="modal-content" style={{ background:'#fff', borderRadius:'8px', padding:'30px', minWidth:'350px', maxWidth:'95vw', boxShadow:'0 4px 24px rgba(0,0,0,0.18)' }}>
              <h3 className="section-title">Edit Donor</h3>
              <form onSubmit={handleEditDonorSubmit}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                  <input
                    autoComplete="off"
                    type="text"
                    placeholder="Full Name *"
                    value={editDonorForm.name}
                    onChange={e => setEditDonorForm(prev => ({...prev, name: e.target.value}))}
                    required
                  />
                  <input
                    autoComplete="off"
                    type="number"
                    placeholder="Age (18-65) *"
                    min="18"
                    max="65"
                    value={editDonorForm.age}
                    onInput={e => {
                      e.target.value = e.target.value.replace(/[^0-9]/g, '');
                    }}
                    onChange={e => setEditDonorForm(prev => ({...prev, age: e.target.value}))}
                    required
                  />
                  <select
                    value={editDonorForm.gender}
                    onChange={e => setEditDonorForm(prev => ({...prev, gender: e.target.value}))}
                  >
                    {genders.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                  <select
                    value={editDonorForm.blood_group}
                    onChange={e => setEditDonorForm(prev => ({...prev, blood_group: e.target.value}))}
                  >
                    {bloodGroups.map(bg => <option key={bg} value={bg}>{bg}</option>)}
                  </select>
                  <input
                    autoComplete="off"
                    type="tel"
                    placeholder="Contact Number (10 digits) *"
                    value={editDonorForm.contact}
                    onChange={e => {
                      const value = e.target.value.replace(/\D/g, '');
                      if (value.length <= 10) {
                        setEditDonorForm(prev => ({...prev, contact: value}));
                      }
                    }}
                    pattern="[0-9]{10}"
                    maxLength="10"
                    required
                    title="Please enter exactly 10 digits"
                  />
                  <input
                    autoComplete="off"
                    type="email"
                    placeholder="Email"
                    value={editDonorForm.email}
                    onChange={e => setEditDonorForm(prev => ({...prev, email: e.target.value}))}
                    pattern="[^\s@]+@[^\s@]+\.[^\s@]+"
                    title="Please enter a valid email address (e.g., example@domain.com)"
                  />
                </div>
                <textarea
                  autoComplete="off"
                  placeholder="Address"
                  value={editDonorForm.address}
                  onChange={e => setEditDonorForm(prev => ({...prev, address: e.target.value}))}
                  style={{ marginTop: '10px' }}
                />
                <div style={{ marginTop: '15px', display:'flex', gap:'10px' }}>
                  <button type="submit" className="button" disabled={loading}>{loading ? 'Saving...' : 'Save Changes'}</button>
                  <button type="button" className="button" style={{ background:'#e5e7eb', color:'#111' }} onClick={closeEditDonorModal}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Donor Modal */}
        {showDeleteModal && (
          <div className="modal-overlay" style={{ position: 'fixed', top:0, left:0, width:'100vw', height:'100vh', background:'rgba(0,0,0,0.3)', zIndex:2000, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div className="modal-content" style={{ background:'#fff', borderRadius:'8px', padding:'30px', minWidth:'320px', maxWidth:'95vw', boxShadow:'0 4px 24px rgba(0,0,0,0.18)' }}>
              <h3 className="section-title">Delete Donor</h3>
              <p>Are you sure you want to delete this donor? This action cannot be undone.</p>
              <div style={{ marginTop: '20px', display:'flex', gap:'10px' }}>
                <button className="button" style={{ background:'#ef4444' }} onClick={handleDeleteDonor} disabled={loading}>{loading ? 'Deleting...' : 'Delete'}</button>
                <button className="button" style={{ background:'#e5e7eb', color:'#111' }} onClick={closeDeleteDonorModal}>Cancel</button>
              </div>
            </div>
          </div>
        )}

        {/* Donors List Table */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Donors List</h3>
          <div className="table-container">
            {donors.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Age</th>
                    <th>Blood Group</th>
                    <th>Contact</th>
                    <th>Total Donations</th>
                    <th>Last Donation</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {donors.map(donor => {
                    const isHighlighted = donorSearchResult === donor.DonorID;
                    return (
                      <tr key={donor.DonorID} style={isHighlighted ? { background: '#fef9c3', fontWeight: 600 } : {}}>
                        <td>{donor.DonorID}</td>
                        <td>{donor.DonorName}</td>
                        <td>{donor.Age}</td>
                        <td><strong>{donor.BloodGroup}</strong></td>
                        <td>{donor.ContactNo}</td>
                        <td>{donor.TotalDonations}</td>
                        <td>{donor.LastDonationDate || 'Never'}</td>
                        <td>
                          <button className="button" style={{ padding:'4px 10px', fontSize:'0.9rem', marginRight:'6px' }} onClick={() => openEditDonorModal(donor)} disabled={loading}>Edit</button>
                          <button className="button" style={{ padding:'4px 10px', fontSize:'0.9rem', background:'#ef4444' }} onClick={() => openDeleteDonorModal(donor.DonorID)} disabled={loading}>Delete</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No donors found</p>
            )}
          </div>
        </div>
      </div>
    );
  }, [donorForm, donors, loading, handleAddDonor, showMessage, genders, bloodGroups, messageTimerRef, showEditModal, editDonorForm, showDeleteModal]);

  const PatientsView = useMemo(() => {
    return (
      <div className="patients-container">
        <h2 className="section-title">Manage Patients</h2>

        {/* Patient Search Box */}
        <div style={{ marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input
            type="text"
            placeholder="Search patient by ID, name, or blood group..."
            value={patientSearch}
            onChange={handlePatientSearch}
            style={{ padding: '8px 12px', borderRadius: '5px', border: '1px solid #d1d5db', minWidth: '260px' }}
          />
          {patientSearchMessage && (
            <span style={{ color: '#991b1b', fontSize: '0.98rem', marginLeft: '8px' }}>{patientSearchMessage}</span>
          )}
        </div>

        {/* Register New Patient */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Register New Patient</h3>
          <form onSubmit={handleAddPatient}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <input
                autoComplete="off"
                type="text"
                placeholder="Patient Name *"
                value={patientForm.name}
                onChange={e => setPatientForm(prev => ({...prev, name: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="number"
                placeholder="Age *"
                min="1"
                value={patientForm.age}
                onInput={e => {
                  e.target.value = e.target.value.replace(/[^0-9]/g, '');
                }}
                onChange={e => setPatientForm(prev => ({...prev, age: e.target.value}))}
                required
              />
              <select
                value={patientForm.gender}
                onChange={e => setPatientForm(prev => ({...prev, gender: e.target.value}))}
              >
                {genders.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
              <select
                value={patientForm.blood_group}
                onChange={e => setPatientForm(prev => ({...prev, blood_group: e.target.value}))}
              >
                {bloodGroups.map(bg => <option key={bg} value={bg}>{bg}</option>)}
              </select>
              <select
                value={patientForm.hospital_id}
                onChange={e => setPatientForm(prev => ({...prev, hospital_id: e.target.value}))}
                required
              >
                <option value="">Select Hospital *</option>
                {hospitals.map(h => <option key={h.HospitalID} value={h.HospitalID}>{h.HospitalName}</option>)}
              </select>
              <input
                autoComplete="off"
                type="tel"
                placeholder="Contact Number (10 digits) *"
                value={patientForm.contact}
                onChange={e => {
                  const value = e.target.value.replace(/\D/g, '');
                  if (value.length <= 10) {
                    setPatientForm(prev => ({...prev, contact: value}));
                  }
                }}
                pattern="[0-9]{10}"
                maxLength="10"
                required
                title="Please enter exactly 10 digits"
              />
            </div>
            <textarea
              autoComplete="off"
              placeholder="Medical Condition"
              value={patientForm.condition}
              onChange={e => setPatientForm(prev => ({...prev, condition: e.target.value}))}
              style={{ marginTop: '10px' }}
            />
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Registering...' : 'Register Patient'}
            </button>
          </form>
        </div>

        {/* Edit Patient Modal */}
        {showEditPatientModal && (
          <div className="modal-overlay" style={{ position: 'fixed', top:0, left:0, width:'100vw', height:'100vh', background:'rgba(0,0,0,0.3)', zIndex:2000, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div className="modal-content" style={{ background:'#fff', borderRadius:'8px', padding:'30px', minWidth:'350px', maxWidth:'95vw', boxShadow:'0 4px 24px rgba(0,0,0,0.18)' }}>
              <h3 className="section-title">Edit Patient</h3>
              <form onSubmit={handleEditPatientSubmit}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                  <input
                    autoComplete="off"
                    type="text"
                    placeholder="Patient Name *"
                    value={editPatientForm.name}
                    onChange={e => setEditPatientForm(prev => ({...prev, name: e.target.value}))}
                    required
                  />
                  <input
                    autoComplete="off"
                    type="number"
                    placeholder="Age *"
                    min="1"
                    value={editPatientForm.age}
                    onInput={e => {
                      e.target.value = e.target.value.replace(/[^0-9]/g, '');
                    }}
                    onChange={e => setEditPatientForm(prev => ({...prev, age: e.target.value}))}
                    required
                  />
                  <select
                    value={editPatientForm.gender}
                    onChange={e => setEditPatientForm(prev => ({...prev, gender: e.target.value}))}
                  >
                    {genders.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                  <select
                    value={editPatientForm.blood_group}
                    onChange={e => setEditPatientForm(prev => ({...prev, blood_group: e.target.value}))}
                  >
                    {bloodGroups.map(bg => <option key={bg} value={bg}>{bg}</option>)}
                  </select>
                  <select
                    value={editPatientForm.hospital_id}
                    onChange={e => setEditPatientForm(prev => ({...prev, hospital_id: e.target.value}))}
                    required
                  >
                    <option value="">Select Hospital *</option>
                    {hospitals.map(h => <option key={h.HospitalID} value={h.HospitalID}>{h.HospitalName}</option>)}
                  </select>
                  <input
                    autoComplete="off"
                    type="tel"
                    placeholder="Contact Number (10 digits) *"
                    value={editPatientForm.contact}
                    onChange={e => {
                      const value = e.target.value.replace(/\D/g, '');
                      if (value.length <= 10) {
                        setEditPatientForm(prev => ({...prev, contact: value}));
                      }
                    }}
                    pattern="[0-9]{10}"
                    maxLength="10"
                    required
                    title="Please enter exactly 10 digits"
                  />
                </div>
                <textarea
                  autoComplete="off"
                  placeholder="Medical Condition"
                  value={editPatientForm.condition}
                  onChange={e => setEditPatientForm(prev => ({...prev, condition: e.target.value}))}
                  style={{ marginTop: '10px' }}
                />
                <div style={{ marginTop: '15px', display:'flex', gap:'10px' }}>
                  <button type="submit" className="button" disabled={loading}>{loading ? 'Saving...' : 'Save Changes'}</button>
                  <button type="button" className="button" style={{ background:'#e5e7eb', color:'#111' }} onClick={closeEditPatientModal}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Patient Modal */}
        {showDeletePatientModal && (
          <div className="modal-overlay" style={{ position: 'fixed', top:0, left:0, width:'100vw', height:'100vh', background:'rgba(0,0,0,0.3)', zIndex:2000, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div className="modal-content" style={{ background:'#fff', borderRadius:'8px', padding:'30px', minWidth:'320px', maxWidth:'95vw', boxShadow:'0 4px 24px rgba(0,0,0,0.18)' }}>
              <h3 className="section-title">Delete Patient</h3>
              <p>Are you sure you want to delete this patient? This action cannot be undone.</p>
              <div style={{ marginTop: '20px', display:'flex', gap:'10px' }}>
                <button className="button" style={{ background:'#ef4444' }} onClick={handleDeletePatient} disabled={loading}>{loading ? 'Deleting...' : 'Delete'}</button>
                <button className="button" style={{ background:'#e5e7eb', color:'#111' }} onClick={closeDeletePatientModal}>Cancel</button>
              </div>
            </div>
          </div>
        )}

        {/* Patients List Table */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Patients List</h3>
          <div className="table-container">
            {patients.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Age</th>
                    <th>Blood Group</th>
                    <th>Hospital</th>
                    <th>Contact</th>
                    <th>Condition</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {patients.map(patient => {
                    const isHighlighted = patientSearchResult === patient.PatientID;
                    return (
                      <tr key={patient.PatientID} style={isHighlighted ? { background: '#fef9c3', fontWeight: 600 } : {}}>
                        <td>{patient.PatientID}</td>
                        <td>{patient.PatientName}</td>
                        <td>{patient.Age}</td>
                        <td><strong>{patient.BloodGroupRequired}</strong></td>
                        <td>{patient.HospitalName}</td>
                        <td>{patient.ContactNo}</td>
                        <td>{patient.MedicalCondition || '-'}</td>
                        <td>
                          <button className="button" style={{ padding:'4px 10px', fontSize:'0.9rem', marginRight:'6px' }} onClick={() => openEditPatientModal(patient)} disabled={loading}>Edit</button>
                          <button className="button" style={{ padding:'4px 10px', fontSize:'0.9rem', background:'#ef4444' }} onClick={() => openDeletePatientModal(patient.PatientID)} disabled={loading}>Delete</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No patients found</p>
            )}
          </div>
        </div>
      </div>
    );
  }, [patientForm, patients, loading, handleAddPatient, genders, bloodGroups, hospitals, patientSearch, patientSearchResult, patientSearchMessage, showEditPatientModal, editPatientForm, showDeletePatientModal]);

  const RequestsView = useMemo(() => {
    return (
      <div className="requests-container">
        <h2 className="section-title">Blood Requests</h2>

        {/* Live Message Queue Telemetry Panel */}
        <div className="card" style={{ borderLeft: '4px solid #8b5cf6', background: '#faf5ff', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.3rem' }}>⚡</span>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#6b21a8' }}>
                  Asynchronous Emergency Alert Queue
                </h3>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.82rem', color: '#7e22ce' }}>
                  Decoupled background worker broadcasts high-priority alerts to matching donors without blocking HTTP requests.
                </p>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span className="status-badge" style={{ background: '#f3e8ff', color: '#6b21a8', fontWeight: 700, border: '1px solid #d8b4fe' }}>
                Broker: {queueStatus?.broker || 'Redis 7.0 (Active)'}
              </span>
            </div>
          </div>

          {recentBroadcasts && recentBroadcasts.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#6b21a8', textTransform: 'uppercase' }}>
                Recent Background Dispatches:
              </div>
              {recentBroadcasts.slice(0, 3).map((bc, idx) => (
                <div key={idx} style={{ background: '#ffffff', padding: '8px 12px', borderRadius: '6px', border: '1px solid #e9d5ff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: 700, color: '#991b1b' }}>🚨 Urgent {bc.blood_group}</span> for <strong>{bc.patient_name}</strong> at <em>{bc.hospital_name}</em>
                    <div style={{ fontSize: '0.78rem', color: '#6b7280', marginTop: '2px' }}>
                      Compatible Groups: {bc.compatible_groups?.join(', ')} | Latency: {bc.processing_time_ms}ms
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className="status-badge fulfilled" style={{ fontSize: '0.8rem' }}>
                      ✓ {bc.notified_count} Donors Alerted
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '0.82rem', color: '#6b7280', fontStyle: 'italic', marginTop: '6px' }}>
              Ready. When an emergency blood request is submitted, compatible donors will be matched and alerted asynchronously.
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Create New Request</h3>
          <form onSubmit={handleCreateRequest}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <select
                value={requestForm.patient_id}
                onChange={e => setRequestForm(prev => ({...prev, patient_id: e.target.value}))}
                required
              >
                <option value="">Select Patient *</option>
                {patients.map(p => <option key={p.PatientID} value={p.PatientID}>{p.PatientName} ({p.BloodGroupRequired})</option>)}
              </select>
              <select
                value={requestForm.blood_bank_id}
                onChange={e => setRequestForm(prev => ({...prev, blood_bank_id: e.target.value}))}
                required
              >
                <option value="">Select Blood Bank *</option>
                {bloodBanks.map(b => <option key={b.BloodBankID} value={b.BloodBankID}>{b.BloodBankName}</option>)}
              </select>
              <input
                autoComplete="off"
                type="number"
                placeholder="Required Units *"
                min="1"
                value={requestForm.required_units}
                onChange={e => setRequestForm(prev => ({...prev, required_units: e.target.value}))}
                required
              />
            </div>
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Creating...' : 'Create Request'}
            </button>
          </form>
        </div>

        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Pending Requests</h3>
          <div className="table-container">
            {requests.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Patient</th>
                    <th>Blood Group</th>
                    <th>Units</th>
                    <th>Blood Bank</th>
                    <th>Status</th>
                    <th>Request Date</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map(req => (
                    <tr key={req.RequestID}>
                      <td>{req.RequestID}</td>
                      <td>{req.PatientName}</td>
                      <td><strong>{req.BloodGroupRequired}</strong></td>
                      <td>{req.RequiredUnits}</td>
                      <td>{req.BloodBankName}</td>
                      <td>
                        <span className={`status-badge ${req.Status?.toLowerCase()}`}>
                          {req.Status}
                        </span>
                      </td>
                      <td>{new Date(req.RequestDate).toLocaleDateString()}</td>
                      <td>
                        <button className="button" style={{ padding:'4px 10px', fontSize:'0.9rem', marginRight:'6px' }} onClick={() => openEditRequestModal(req)} disabled={loading}>Edit</button>
                        <button className="button" style={{ padding:'4px 10px', fontSize:'0.9rem', background:'#ef4444' }} onClick={() => openDeleteRequestModal(req)} disabled={loading}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No requests found</p>
            )}
          </div>
        </div>
        {/* Edit Request Modal */}
        {showEditRequestModal && (
          <div className="modal-overlay" style={{ position: 'fixed', top:0, left:0, width:'100vw', height:'100vh', background:'rgba(0,0,0,0.3)', zIndex:2000, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div className="modal-content" style={{ background:'#fff', borderRadius:'8px', padding:'30px', minWidth:'350px', maxWidth:'95vw', boxShadow:'0 4px 24px rgba(0,0,0,0.18)' }}>
              <h3 className="section-title">Edit Request</h3>
              <form onSubmit={handleEditRequestSubmit}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                  <select
                    value={editRequestForm.patient_id}
                    onChange={e => setEditRequestForm(prev => ({...prev, patient_id: e.target.value}))}
                    required
                  >
                    <option value="">Select Patient *</option>
                    {patients.map(p => <option key={p.PatientID} value={p.PatientID}>{p.PatientName} ({p.BloodGroupRequired})</option>)}
                  </select>
                  <select
                    value={editRequestForm.blood_bank_id}
                    onChange={e => setEditRequestForm(prev => ({...prev, blood_bank_id: e.target.value}))}
                    required
                  >
                    <option value="">Select Blood Bank *</option>
                    {bloodBanks.map(b => <option key={b.BloodBankID} value={b.BloodBankID}>{b.BloodBankName}</option>)}
                  </select>
                  <input
                    autoComplete="off"
                    type="number"
                    placeholder="Required Units *"
                    min="1"
                    value={editRequestForm.required_units}
                    onChange={e => setEditRequestForm(prev => ({...prev, required_units: e.target.value}))}
                    required
                  />
                </div>
                <div style={{ marginTop: '15px', display:'flex', gap:'10px' }}>
                  <button type="submit" className="button" disabled={loading}>{loading ? 'Saving...' : 'Save Changes'}</button>
                  <button type="button" className="button" style={{ background:'#e5e7eb', color:'#111' }} onClick={closeEditRequestModal}>Cancel</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Delete Request Modal */}
        {showDeleteRequestModal && (
          <div className="modal-overlay" style={{ position: 'fixed', top:0, left:0, width:'100vw', height:'100vh', background:'rgba(0,0,0,0.3)', zIndex:2000, display:'flex', alignItems:'center', justifyContent:'center' }}>
            <div className="modal-content" style={{ background:'#fff', borderRadius:'8px', padding:'30px', minWidth:'320px', maxWidth:'95vw', boxShadow:'0 4px 24px rgba(0,0,0,0.18)' }}>
              <h3 className="section-title">Delete Request</h3>
              <p>Are you sure you want to delete this request? This action cannot be undone.</p>
              <div style={{ marginTop: '20px', display:'flex', gap:'10px' }}>
                <button className="button" style={{ background:'#ef4444' }} onClick={handleDeleteRequest} disabled={loading}>{loading ? 'Deleting...' : 'Delete'}</button>
                <button className="button" style={{ background:'#e5e7eb', color:'#111' }} onClick={closeDeleteRequestModal}>Cancel</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }, [requestForm, patients, bloodBanks, loading, handleCreateRequest, requests, showEditRequestModal, editRequestForm, showDeleteRequestModal]);

  const ManagementView = useMemo(() => {
    return (
      <div className="management-container">
        <h2 className="section-title">System Management</h2>

        {/* Record Donation */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Record Blood Donation</h3>
          <form onSubmit={handleRecordDonation}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <select
                value={donationForm.donor_id}
                onChange={e => setDonationForm(prev => ({...prev, donor_id: e.target.value}))}
                required
              >
                <option value="">Select Donor *</option>
                {donors.map(d => <option key={d.DonorID} value={d.DonorID}>{d.DonorName} ({d.BloodGroup})</option>)}
              </select>
              <select
                value={donationForm.blood_bank_id}
                onChange={e => setDonationForm(prev => ({...prev, blood_bank_id: e.target.value}))}
                required
              >
                <option value="">Select Blood Bank *</option>
                {bloodBanks.map(b => <option key={b.BloodBankID} value={b.BloodBankID}>{b.BloodBankName}</option>)}
              </select>
              <select
                value={donationForm.component}
                onChange={e => setDonationForm(prev => ({...prev, component: e.target.value}))}
              >
                {components.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <input
                autoComplete="off"
                type="number"
                placeholder="Quantity *"
                min="1"
                value={donationForm.quantity}
                onChange={e => setDonationForm(prev => ({...prev, quantity: e.target.value}))}
                required
              />
            </div>
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Recording...' : 'Record Donation'}
            </button>
          </form>
        </div>

        {/* Allocate Blood */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Allocate Blood Units</h3>
          <form onSubmit={handleAllocateBlood}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <select
                value={allocationForm.request_id}
                onChange={e => {
                  setAllocationForm(prev => ({...prev, request_id: e.target.value, unit_id: ''}));
                }}
                required
              >
                <option value="">Select Request *</option>
                {requests.filter(r => r.Status === 'Pending').map(r => 
                  <option key={r.RequestID} value={r.RequestID}>
                    {r.PatientName} - {r.BloodGroupRequired} ({r.RequiredUnits} units)
                  </option>
                )}
              </select>
              <select
                value={allocationForm.unit_id}
                onChange={e => setAllocationForm(prev => ({...prev, unit_id: e.target.value}))}
                required
                disabled={!allocationForm.request_id}
              >
                <option value="">
                  {!allocationForm.request_id ? 'Select Request First' : 'Select Blood Unit *'}
                </option>
                {allocationForm.request_id && (
                  <option value="no_match" style={{ color: '#dc2626', fontWeight: 'bold' }}>
                    ❌ No Matching Blood Type Available - Deny Request
                  </option>
                )}
                {(() => {
                  const selectedRequest = requests.find(r => r.RequestID === parseInt(allocationForm.request_id));
                  const requiredBloodGroup = selectedRequest?.BloodGroupRequired;
                  const availableUnits = bloodUnits.filter(u => u.Status === 'Available');
                  const matchingUnits = availableUnits.filter(u => u.BloodGroup === requiredBloodGroup);
                  const nonMatchingUnits = availableUnits.filter(u => u.BloodGroup !== requiredBloodGroup);
                  
                  return (
                    <>
                      {matchingUnits.length > 0 && (
                        <optgroup label={`✓ Matching Blood Type (${requiredBloodGroup})`}>
                          {matchingUnits.map(u => 
                            <option key={u.UnitID} value={u.UnitID}>
                              Unit {u.UnitID} - {u.BloodGroup} ({u.Component}) - Expires: {new Date(u.ExpirationDate).toLocaleDateString()}
                            </option>
                          )}
                        </optgroup>
                      )}
                      {nonMatchingUnits.length > 0 && (
                        <optgroup label="⚠ Non-Matching Blood Types (Will be Denied)">
                          {nonMatchingUnits.map(u => 
                            <option key={u.UnitID} value={u.UnitID}>
                              Unit {u.UnitID} - {u.BloodGroup} ({u.Component}) - Expires: {new Date(u.ExpirationDate).toLocaleDateString()}
                            </option>
                          )}
                        </optgroup>
                      )}
                    </>
                  );
                })()}
              </select>
            </div>
            {allocationForm.request_id && (() => {
              const selectedRequest = requests.find(r => r.RequestID === parseInt(allocationForm.request_id));
              const isNoMatch = allocationForm.unit_id === 'no_match';
              return selectedRequest ? (
                <div style={{ 
                  marginTop: '10px', 
                  padding: '10px', 
                  background: isNoMatch ? '#fef2f2' : '#f3f4f6', 
                  borderRadius: '5px',
                  fontSize: '0.95rem',
                  border: isNoMatch ? '1px solid #fca5a5' : 'none'
                }}>
                  <strong>Request Details:</strong> Patient {selectedRequest.PatientName} requires <strong>{selectedRequest.BloodGroupRequired}</strong> blood type ({selectedRequest.RequiredUnits} units needed)
                  {isNoMatch && (
                    <div style={{ marginTop: '8px', color: '#dc2626', fontWeight: '500' }}>
                      ⚠️ Warning: This request will be marked as DENIED with no blood allocated.
                    </div>
                  )}
                </div>
              ) : null;
            })()}
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? (allocationForm.unit_id === 'no_match' ? 'Denying...' : 'Allocating...') : (allocationForm.unit_id === 'no_match' ? 'Deny Request' : 'Allocate Blood')}
            </button>
          </form>
        </div>

        {/* Add Hospital */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Add Hospital</h3>
          <form onSubmit={handleAddHospital}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <input
                autoComplete="off"
                type="text"
                placeholder="Hospital Name *"
                value={hospitalForm.name}
                onChange={e => setHospitalForm(prev => ({...prev, name: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="text"
                placeholder="Location *"
                value={hospitalForm.location}
                onChange={e => setHospitalForm(prev => ({...prev, location: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="tel"
                placeholder="Contact Number *"
                value={hospitalForm.contact}
                onChange={e => setHospitalForm(prev => ({...prev, contact: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="email"
                placeholder="Email"
                value={hospitalForm.email}
                onChange={e => setHospitalForm(prev => ({...prev, email: e.target.value}))}
              />
            </div>
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Adding...' : 'Add Hospital'}
            </button>
          </form>
        </div>

        {/* Add Blood Bank */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Add Blood Bank</h3>
          <form onSubmit={handleAddBloodBank}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
              <input
                autoComplete="off"
                type="text"
                placeholder="Blood Bank Name *"
                value={bloodBankForm.name}
                onChange={e => setBloodBankForm(prev => ({...prev, name: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="text"
                placeholder="Location *"
                value={bloodBankForm.location}
                onChange={e => setBloodBankForm(prev => ({...prev, location: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="tel"
                placeholder="Contact Number *"
                value={bloodBankForm.contact}
                onChange={e => setBloodBankForm(prev => ({...prev, contact: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="number"
                placeholder="Capacity"
                min="100"
                value={bloodBankForm.capacity}
                onChange={e => setBloodBankForm(prev => ({...prev, capacity: e.target.value}))}
              />
            </div>
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Adding...' : 'Add Blood Bank'}
            </button>
          </form>
        </div>

        {/* Inventory View */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Blood Inventory</h3>
          <div className="table-container">
            {inventory.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Blood Bank</th>
                    <th>Blood Group</th>
                    <th>Total Units</th>
                    <th>Total Quantity</th>
                    <th>Days Until Expiry</th>
                  </tr>
                </thead>
                <tbody>
                  {inventory.map((inv, idx) => (
                    <tr key={idx}>
                      <td>{inv.BloodBankName}</td>
                      <td><strong>{inv.BloodGroup}</strong></td>
                      <td>{inv.TotalUnits}</td>
                      <td>{inv.TotalQuantity}</td>
                      <td>{inv.DaysUntilExpiry || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No inventory data available</p>
            )}
          </div>
        </div>

        {/* Recent Allocations */}
        <div className="card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Recent Allocations & Request History</h3>
          <div className="table-container">
            {allocations.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Allocation ID</th>
                    <th>Request ID</th>
                    <th>Patient</th>
                    <th>Blood Group</th>
                    <th>Blood Bank</th>
                    <th>Component</th>
                    <th>Status</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {allocations.slice(0, 20).map(allocation => {
                    const isFailed = allocation.DeliveryStatus === 'Failed';
                    return (
                      <tr key={allocation.AllocationID} style={{ background: isFailed ? '#fef2f2' : 'transparent' }}>
                        <td>{allocation.AllocationID}</td>
                        <td>{allocation.RequestID}</td>
                        <td>{allocation.PatientName}</td>
                        <td><strong>{allocation.BloodGroup}</strong></td>
                        <td>{allocation.BloodBankName}</td>
                        <td>{allocation.Component}</td>
                        <td>
                          <span className={`status-badge ${isFailed ? 'denied' : allocation.DeliveryStatus?.toLowerCase() || 'pending'}`}>
                            {isFailed ? 'Denied (Mismatch)' : allocation.DeliveryStatus || 'Fulfilled'}
                          </span>
                        </td>
                        <td>{new Date(allocation.AllocationDate).toLocaleString()}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No allocations recorded yet</p>
            )}
          </div>
        </div>
      </div>
    );
  }, [donationForm, donors, bloodBanks, components, loading, handleRecordDonation, allocationForm, requests, bloodUnits, handleAllocateBlood, hospitalForm, handleAddHospital, bloodBankForm, handleAddBloodBank, inventory, allocations]);

  // Donor Portal View
  const DonorPortalView = (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 className="section-title" style={{ margin: 0 }}>Welcome to Your Donor Portal</h2>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0' }}>Manage your profile, view medical eligibility, and review donation history</p>
        </div>
        <button className="button" onClick={fetchDonorPortal} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {donorPortalLoading ? (
        <p style={{ textAlign: 'center', color: '#6b7280' }}>Loading your donor records...</p>
      ) : (
        <>
          {/* Eligibility Box */}
          <div className={`eligibility-alert ${donorPortalData.eligibility?.includes('ELIGIBLE') && !donorPortalData.eligibility?.includes('NOT') ? 'eligible' : 'not-eligible'}`}>
            <Award size={24} />
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>Donation Eligibility Status</div>
              <div>{donorPortalData.eligibility || 'Check with your local blood center'}</div>
            </div>
          </div>

          {/* Donor Stats Grid */}
          <div className="portal-grid">
            <div className="card" style={{ borderLeft: '4px solid #dc2626' }}>
              <div style={{ color: '#6b7280', fontSize: '0.9rem', fontWeight: 600 }}>DONOR DETAILS</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '6px' }}>{auth?.user?.name}</div>
              <div style={{ color: '#4b5563', marginTop: '4px' }}>Email: {auth?.user?.email}</div>
              <div style={{ marginTop: '8px' }}>
                <span className="status-badge" style={{ background: '#fee2e2', color: '#991b1b', fontWeight: 700 }}>
                  Blood Group: {donorPortalData.donor?.BloodGroup || 'Pending'}
                </span>
              </div>
            </div>

            <div className="card" style={{ borderLeft: '4px solid #16a34a' }}>
              <div style={{ color: '#6b7280', fontSize: '0.9rem', fontWeight: 600 }}>TOTAL DONATIONS</div>
              <div className="stat-metric">{donorPortalData.donor?.TotalDonations ?? 0}</div>
              <div style={{ color: '#4b5563', fontSize: '0.85rem' }}>Units donated to date</div>
            </div>

            <div className="card" style={{ borderLeft: '4px solid #2563eb' }}>
              <div style={{ color: '#6b7280', fontSize: '0.9rem', fontWeight: 600 }}>LAST DONATION</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '8px', color: '#1e40af' }}>
                {donorPortalData.donor?.LastDonationDate || 'First-time donor'}
              </div>
              <div style={{ color: '#4b5563', fontSize: '0.85rem', marginTop: '4px' }}>Registered: {donorPortalData.donor?.RegistrationDate?.slice(0, 10) || 'Active'}</div>
            </div>
          </div>

          {/* Donation History Table */}
          <div className="card">
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#991b1b', marginBottom: '14px' }}>
              📜 Your Donation Records
            </h3>
            {donorPortalData.donation_history && donorPortalData.donation_history.length > 0 ? (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Unit ID</th>
                      <th>Blood Bank</th>
                      <th>Location</th>
                      <th>Blood Group</th>
                      <th>Component</th>
                      <th>Collection Date</th>
                      <th>Expiration Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {donorPortalData.donation_history.map(item => (
                      <tr key={item.UnitID}>
                        <td>#{item.UnitID}</td>
                        <td style={{ fontWeight: 600 }}>{item.BloodBankName}</td>
                        <td>{item.Location}</td>
                        <td><span className="status-badge" style={{ background: '#fee2e2', color: '#991b1b' }}>{item.BloodGroup}</span></td>
                        <td>{item.Component}</td>
                        <td>{item.CollectionDate}</td>
                        <td>{item.ExpirationDate}</td>
                        <td>
                          <span className={`status-badge ${item.Status === 'Available' ? 'fulfilled' : item.Status === 'Reserved' ? 'pending' : 'denied'}`}>
                            {item.Status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: '#6b7280', padding: '12px 0' }}>No past donations found under your profile yet. Visit a nearby blood center to donate!</p>
            )}
          </div>

          {/* Nearby Blood Banks */}
          <div className="card">
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#991b1b', marginBottom: '14px' }}>
              🏥 Authorized Blood Centers
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
              {(donorPortalData.bloodbanks || bloodBanks).map(bank => (
                <div key={bank.BloodBankID} style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '14px', background: '#fafafa' }}>
                  <div style={{ fontWeight: 700, color: '#1f2937' }}>{bank.BloodBankName}</div>
                  <div style={{ color: '#4b5563', fontSize: '0.9rem', marginTop: '4px' }}>📍 {bank.Location}</div>
                  <div style={{ color: '#4b5563', fontSize: '0.9rem' }}>📞 {bank.ContactNo}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );

  // Shared Auth Form UI for both Modal and Gateway
  const renderAuthForm = (isModal = false) => {
    return (
      <div className={isModal ? "auth-container" : "card"} style={isModal ? { margin: 0, position: 'relative', width: '100%' } : { padding: '36px', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)' }}>
        {isModal && (
          <button
            onClick={() => setShowAuthModal(false)}
            style={{ position: 'absolute', top: '16px', right: '16px', border: 'none', background: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#6b7280' }}
          >
            ✕
          </button>
        )}

        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '56px', height: '56px', borderRadius: '50%', background: '#fee2e2', color: '#dc2626', marginBottom: '12px' }}>
            <Shield size={28} />
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#111827', margin: 0 }}>
            {authMode === 'login' ? 'Sign In to Portal' : registerStep === 'otp' ? 'Verify Email Address' : 'Create an Account'}
          </h2>
          <p style={{ color: '#6b7280', marginTop: '6px', fontSize: '0.92rem' }}>
            {authMode === 'login' 
              ? 'Access real-time blood stock, emergency allocations, and donor records'
              : registerStep === 'otp'
              ? `Enter the 6-digit verification code sent to ${registerForm.email}`
              : 'Register as a Donor, Hospital Staff, or Blood Bank Admin'}
          </p>
        </div>

        {/* 1-Click Fast Demo Accounts */}
        {registerStep === 'form' && (
          <div style={{ marginBottom: '20px', background: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#475569', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Fast 1-Click Demo Sign-In
            </div>
            <div className="demo-pills">
              <button type="button" className="demo-btn" onClick={() => handleQuickDemoLogin('admin@bloodbank.org', 'Admin@123')}>
                <span>Admin Portal</span>
                <small>admin@bloodbank.org</small>
              </button>
              <button type="button" className="demo-btn" onClick={() => handleQuickDemoLogin('superadmin@bloodbank.org', 'SuperAdmin@123')}>
                <span>Global Super Admin</span>
                <small>superadmin@bloodbank.org</small>
              </button>
              <button type="button" className="demo-btn" onClick={() => handleQuickDemoLogin('alice@example.com', 'Donor@123')}>
                <span>Donor Portal</span>
                <small>alice@example.com</small>
              </button>
              <button type="button" className="demo-btn" onClick={() => handleQuickDemoLogin('hospital@citycare.org', 'Hospital@123')}>
                <span>Hospital Staff</span>
                <small>hospital@citycare.org</small>
              </button>
            </div>
          </div>
        )}

        {/* Mode Switcher: Sign In vs Create Account */}
        {registerStep === 'form' && (
          <div style={{ display: 'flex', borderBottom: '1px solid #e5e7eb', marginBottom: '20px' }}>
            <button
              type="button"
              onClick={() => { setAuthMode('login'); setLoginOtpSent(false); }}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                background: 'none',
                fontWeight: 700,
                cursor: 'pointer',
                fontSize: '0.95rem',
                color: authMode === 'login' ? '#991b1b' : '#6b7280',
                borderBottom: authMode === 'login' ? '2px solid #991b1b' : 'none'
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setAuthMode('register'); setRegisterStep('form'); }}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                background: 'none',
                fontWeight: 700,
                cursor: 'pointer',
                fontSize: '0.95rem',
                color: authMode === 'register' ? '#991b1b' : '#6b7280',
                borderBottom: authMode === 'register' ? '2px solid #991b1b' : 'none'
              }}
            >
              Create Account (with Email OTP)
            </button>
          </div>
        )}

        {authMode === 'login' ? (
          <div>
            {/* Login Method Sub-Toggle */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button
                type="button"
                onClick={() => { setLoginMethod('password'); setLoginOtpSent(false); }}
                style={{
                  flex: 1,
                  padding: '7px 12px',
                  borderRadius: '6px',
                  border: loginMethod === 'password' ? '1px solid #991b1b' : '1px solid #d1d5db',
                  background: loginMethod === 'password' ? '#fee2e2' : '#ffffff',
                  color: loginMethod === 'password' ? '#991b1b' : '#4b5563',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Password Login
              </button>
              <button
                type="button"
                onClick={() => setLoginMethod('otp')}
                style={{
                  flex: 1,
                  padding: '7px 12px',
                  borderRadius: '6px',
                  border: loginMethod === 'otp' ? '1px solid #991b1b' : '1px solid #d1d5db',
                  background: loginMethod === 'otp' ? '#fee2e2' : '#ffffff',
                  color: loginMethod === 'otp' ? '#991b1b' : '#4b5563',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Email OTP Login
              </button>
            </div>

            {loginMethod === 'password' ? (
              <form onSubmit={handleLoginSubmit}>
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '5px', color: '#374151' }}>Email Address</label>
                  <input
                    type="email"
                    value={loginForm.email}
                    onChange={e => setLoginForm(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="e.g. admin@bloodbank.org"
                    required
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                  />
                </div>
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '5px', color: '#374151' }}>Password</label>
                  <input
                    type="password"
                    value={loginForm.password}
                    onChange={e => setLoginForm(prev => ({ ...prev, password: e.target.value }))}
                    placeholder="••••••••"
                    required
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                  />
                </div>
                <button type="submit" className="button" disabled={loading} style={{ width: '100%', padding: '11px', fontSize: '0.95rem', fontWeight: 700 }}>
                  {loading ? 'Authenticating...' : 'Sign In'}
                </button>
              </form>
            ) : !loginOtpSent ? (
              <form onSubmit={handleSendLoginOTP}>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '5px', color: '#374151' }}>Registered Email Address</label>
                  <input
                    type="email"
                    value={loginForm.email}
                    onChange={e => setLoginForm(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="e.g. alice@example.com"
                    required
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                  />
                  <small style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: '4px', display: 'block' }}>
                    We will send a 6-digit one-time code to your email for passwordless login.
                  </small>
                </div>
                <button type="submit" className="button" disabled={loading} style={{ width: '100%', padding: '11px', fontSize: '0.95rem', fontWeight: 700 }}>
                  {loading ? 'Sending Code...' : 'Send Login OTP'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleVerifyLoginOTP}>
                <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '12px 14px', marginBottom: '18px', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.85rem', color: '#166534', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                    <span>📧</span> Verification code dispatched!
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#15803d', marginTop: '4px' }}>
                    Check your inbox at <strong>{loginForm.email}</strong> and enter the 6-digit code below.
                  </div>
                </div>
                <div style={{ marginBottom: '18px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px', color: '#374151', textAlign: 'center' }}>
                    Enter 6-Digit Login Code
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={loginOtp}
                    onChange={e => setLoginOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="••••••"
                    required
                    autoFocus
                    style={{ width: '100%', padding: '12px', fontSize: '1.5rem', fontWeight: 700, letterSpacing: '8px', textAlign: 'center', fontFamily: 'monospace', borderRadius: '6px', border: '2px solid #dc2626' }}
                  />
                </div>
                <button type="submit" className="button" disabled={loading || loginOtp.length !== 6} style={{ width: '100%', padding: '11px', fontSize: '0.95rem', fontWeight: 700, marginBottom: '12px' }}>
                  {loading ? 'Verifying...' : 'Verify & Sign In'}
                </button>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button
                    type="button"
                    onClick={handleResendLoginOTP}
                    disabled={otpTimer > 0 || loading}
                    style={{ background: 'none', border: 'none', color: otpTimer > 0 ? '#9ca3af' : '#991b1b', fontSize: '0.85rem', fontWeight: 600, cursor: otpTimer > 0 ? 'default' : 'pointer' }}
                  >
                    {otpTimer > 0 ? `Resend code in ${otpTimer}s` : 'Resend Code'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setLoginOtpSent(false); setLoginOtp(''); }}
                    style={{ background: 'none', border: 'none', color: '#4b5563', fontSize: '0.85rem', cursor: 'pointer' }}
                  >
                    ← Change Email
                  </button>
                </div>
              </form>
            )}
          </div>
        ) : registerStep === 'form' ? (
          <form onSubmit={handleSendRegisterOTP}>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Full Name *</label>
              <input
                type="text"
                value={registerForm.full_name}
                onChange={e => setRegisterForm(prev => ({ ...prev, full_name: e.target.value }))}
                placeholder="Jane Doe"
                required
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Email Address *</label>
                <input
                  type="email"
                  value={registerForm.email}
                  onChange={e => setRegisterForm(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="user@example.com"
                  required
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Password * (Min 6)</label>
                <input
                  type="password"
                  value={registerForm.password}
                  onChange={e => setRegisterForm(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="••••••••"
                  minLength={6}
                  required
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Role *</label>
              <select
                value={registerForm.role}
                onChange={e => setRegisterForm(prev => ({ ...prev, role: e.target.value }))}
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
              >
                <option value="Donor">Donor (Self-Service Profile & Eligibility)</option>
                <option value="Hospital">Hospital Staff (Emergency Blood Requests)</option>
                <option value="Admin">Blood Bank Admin (Inventory & Management)</option>
              </select>
            </div>

            {registerForm.role === 'Donor' && (
              <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '6px', marginBottom: '14px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#991b1b', marginBottom: '8px' }}>Donor Profile Details (for automated eligibility)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Age (18-65)</label>
                    <input
                      type="number"
                      min="18"
                      max="65"
                      placeholder="25"
                      value={registerForm.age}
                      onChange={e => setRegisterForm(prev => ({ ...prev, age: e.target.value }))}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Gender</label>
                    <select
                      value={registerForm.gender}
                      onChange={e => setRegisterForm(prev => ({ ...prev, gender: e.target.value }))}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    >
                      <option value="M">Male</option>
                      <option value="F">Female</option>
                      <option value="O">Other</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Blood Group</label>
                    <select
                      value={registerForm.blood_group}
                      onChange={e => setRegisterForm(prev => ({ ...prev, blood_group: e.target.value }))}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    >
                      {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map(bg => (
                        <option key={bg} value={bg}>{bg}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>10-Digit Contact</label>
                    <input
                      type="text"
                      maxLength={10}
                      placeholder="9876543210"
                      value={registerForm.contact}
                      onChange={e => setRegisterForm(prev => ({ ...prev, contact: e.target.value.replace(/\D/g, '') }))}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Address</label>
                    <input
                      type="text"
                      placeholder="City / Street"
                      value={registerForm.address}
                      onChange={e => setRegisterForm(prev => ({ ...prev, address: e.target.value }))}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #d1d5db' }}
                    />
                  </div>
                </div>
              </div>
            )}

            {registerForm.role === 'Hospital' && (
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Associated Hospital</label>
                <select
                  value={registerForm.hospital_id}
                  onChange={e => setRegisterForm(prev => ({ ...prev, hospital_id: e.target.value }))}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                >
                  <option value="">Select an Existing Hospital (or None)</option>
                  {hospitals.map(h => (
                    <option key={h.HospitalID} value={h.HospitalID}>{h.HospitalName} ({h.Location})</option>
                  ))}
                </select>
              </div>
            )}

            {registerForm.role === 'Admin' && (
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '4px', color: '#374151' }}>Associated Blood Bank</label>
                <select
                  value={registerForm.blood_bank_id}
                  onChange={e => setRegisterForm(prev => ({ ...prev, blood_bank_id: e.target.value }))}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
                >
                  <option value="">Select Blood Bank</option>
                  {bloodBanks.map(b => (
                    <option key={b.BloodBankID} value={b.BloodBankID}>{b.BloodBankName} ({b.Location})</option>
                  ))}
                </select>
              </div>
            )}

            <button type="submit" className="button" disabled={loading} style={{ width: '100%', padding: '12px', fontSize: '0.95rem', fontWeight: 700 }}>
              {loading ? 'Sending Verification Code...' : 'Send OTP to Email & Continue'}
            </button>
          </form>
        ) : (
          /* Register Step 2: OTP Verification */
          <form onSubmit={handleVerifyRegisterOTP}>
            <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '12px 14px', marginBottom: '18px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: '#166534', fontWeight: 600 }}>
                Verification code sent to email!
              </div>
              <div style={{ fontSize: '0.8rem', color: '#15803d', marginTop: '4px' }}>
                We sent a 6-digit code to <strong>{registerForm.email}</strong>. Please check your inbox (and spam folder) to verify.
              </div>
            </div>

            <div style={{ marginBottom: '20px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.85rem', color: '#4b5563', marginBottom: '10px' }}>
                Enter the 6-digit code sent to <strong style={{ color: '#111827' }}>{registerForm.email}</strong>
              </div>
              <input
                type="text"
                maxLength={6}
                value={registerOtp}
                onChange={e => setRegisterOtp(e.target.value.replace(/\D/g, ''))}
                placeholder="••••••"
                required
                autoFocus
                style={{ width: '100%', maxWidth: '280px', margin: '0 auto', padding: '12px', fontSize: '1.6rem', fontWeight: 800, letterSpacing: '8px', textAlign: 'center', fontFamily: 'monospace', borderRadius: '8px', border: '2px solid #dc2626' }}
              />
            </div>

            <button type="submit" className="button" disabled={loading || registerOtp.length !== 6} style={{ width: '100%', padding: '12px', fontSize: '1rem', fontWeight: 700, marginBottom: '14px' }}>
              {loading ? 'Verifying...' : 'Verify Code & Complete Registration'}
            </button>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                type="button"
                onClick={handleResendRegisterOTP}
                disabled={otpTimer > 0 || loading}
                style={{ background: 'none', border: 'none', color: otpTimer > 0 ? '#9ca3af' : '#991b1b', fontSize: '0.85rem', fontWeight: 600, cursor: otpTimer > 0 ? 'default' : 'pointer' }}
              >
                {otpTimer > 0 ? `Resend OTP in ${otpTimer}s` : 'Resend Verification Code'}
              </button>
              <button
                type="button"
                onClick={() => { setRegisterStep('form'); setRegisterOtp(''); }}
                style={{ background: 'none', border: 'none', color: '#4b5563', fontSize: '0.85rem', cursor: 'pointer' }}
              >
                ← Edit Information
              </button>
            </div>
          </form>
        )}
      </div>
    );
  };

  // Auth Modal Component
  const AuthModal = (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
      padding: '20px'
    }}>
      {renderAuthForm(true)}
    </div>
  );

  // Compute navigation tabs dynamically based on user role (strictly requires authentication)
  const userRole = auth?.user?.role || null;
  const dynamicTabs = useMemo(() => {
    if (!userRole) {
      return [];
    }
    if (userRole === 'Donor') {
      return [
        { id: 'donor-portal', label: 'Donor Portal' },
        { id: 'network-map', label: 'Live Network Map' },
        { id: 'dashboard', label: 'Statistics' },
      ];
    }
    if (userRole === 'Hospital') {
      return [
        { id: 'requests', label: 'Emergency Requests' },
        { id: 'network-map', label: 'Live Network Map' },
        { id: 'patients', label: 'Patients' },
        { id: 'dashboard', label: 'Statistics' },
      ];
    }
    // Admin / SuperAdmin
    return [
      { id: 'dashboard', label: 'Dashboard' },
      { id: 'network-map', label: 'Live Network Map' },
      { id: 'donors', label: 'Donors' },
      { id: 'patients', label: 'Patients' },
      { id: 'requests', label: 'Requests' },
      { id: 'management', label: 'Management' },
      ...(auth?.user?.donor_id ? [{ id: 'donor-portal', label: 'Donor Portal' }] : []),
    ];
  }, [userRole, auth]);

  return (
    <div>
      {message && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          padding: '15px 20px',
          background: messageType === 'success' ? '#dcfce7' : '#fef2f2',
          color: messageType === 'success' ? '#166534' : '#991b1b',
          borderRadius: '6px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          zIndex: 1000,
          border: `1px solid ${messageType === 'success' ? '#86efac' : '#fca5a5'}`
        }}>
          {message}
        </div>
      )}

      {showAuthModal && AuthModal}

      <header className="header">
        <div className="header-inner" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Heart className="header-icon" fill="white" />
            <div>
              <span className="title">Blood Bank Management System</span>
              <div style={{ fontSize: '13px', opacity: 0.85 }}>Enterprise Healthcare & Donor Allocation Network</div>
            </div>
          </div>

          <div className="header-user">
            {auth?.user ? (
              <>
                <span className={`role-badge ${auth.user.role.toLowerCase()}`}>
                  <Shield size={12} /> {auth.user.role}
                </span>
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{auth.user.name}</span>
                <button className="btn-logout" onClick={handleLogout} title="Sign out">
                  <LogOut size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Logout
                </button>
              </>
            ) : (
              <button className="btn-logout" onClick={() => setShowAuthModal(true)} style={{ background: '#fff', color: '#991b1b', fontWeight: 700 }}>
                <LogIn size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Sign In / Demo Login
              </button>
            )}
          </div>
        </div>
      </header>

      {!auth?.user ? (
        /* Unauthenticated Gateway — Strictly prevents access to portals until signed in */
        <div className="container" style={{ maxWidth: '640px', marginTop: '40px', marginBottom: '60px' }}>
          {renderAuthForm(false)}
        </div>
      ) : (
        <>
          <div className="tabs">
            {dynamicTabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-button${activeTab !== tab.id ? ' inactive' : ''}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="container" style={activeTab === 'network-map' ? { maxWidth: '1240px', padding: '20px' } : {}}>
            {activeTab === 'dashboard' && <DashboardView />}
            {activeTab === 'network-map' && (
              <LiveNetworkMap
                donors={donors}
                requests={requests}
                bloodBanks={bloodBanks}
                hospitals={hospitals}
                currentUser={auth?.user}
              />
            )}
            {activeTab === 'donor-portal' && DonorPortalView}
            {activeTab === 'donors' && DonorsView}
            {activeTab === 'patients' && PatientsView}
            {activeTab === 'requests' && RequestsView}
            {activeTab === 'management' && ManagementView}
          </div>
        </>
      )}
    </div>
  );
};

export default BloodBankManagement;

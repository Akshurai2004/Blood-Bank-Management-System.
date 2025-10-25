import React, { useState, useEffect, useRef } from 'react';
import { Heart, Users, Building2, Droplet, AlertCircle, CheckCircle, XCircle } from 'lucide-react';

const ENV_API_BASE = (process.env.REACT_APP_API_URL || '').trim().replace(/\/$/, '');
const DEFAULT_API_BASE = 'http://localhost:8000/api';

const buildApiUrl = (path) => {
  const base = ENV_API_BASE || DEFAULT_API_BASE;
  return `${base}${path}`;
};

const BloodBankManagement = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
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
  const [patientForm, setPatientForm] = useState({
    name: '', age: '', gender: 'M', blood_group: 'A+', hospital_id: '', contact: '', condition: ''
  });
  const [requestForm, setRequestForm] = useState({
    patient_id: '', blood_bank_id: '', required_units: '1'
  });
  const [donationForm, setDonationForm] = useState({
    donor_id: '', blood_bank_id: '', component: 'Whole Blood', quantity: '1'
  });
  const [hospitalForm, setHospitalForm] = useState({
    name: '', location: '', contact: '', email: ''
  });
  const [bloodBankForm, setBloodBankForm] = useState({
    name: '', location: '', contact: '', capacity: '1000'
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

  const request = async (path, options = {}) => {
    const response = await fetch(buildApiUrl(path), options);
    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      // Ignore JSON parse errors and fall back to status handling
    }

    if (!response.ok) {
      const detail = data?.detail || data?.message || `Request failed with status ${response.status}`;
      throw new Error(detail);
    }

    return data;
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const loadAllData = async () => {
      try {
        await Promise.all([
          fetchDonors(),
          fetchBloodBanks(),
          fetchHospitals(),
          fetchPatients(),
          fetchInventory(),
          fetchRequests(),
          fetchStatistics(),
          fetchBloodUnits(),
          fetchAllocations()
        ]);
      } catch (error) {
        console.error('Error during bulk fetch:', error);
      }
    };

    loadAllData();
    // Remove auto-refresh interval to prevent input field focus loss
    // const interval = setInterval(loadAllData, 5000); // Refresh every 5 seconds
    // return () => clearInterval(interval);
  }, []);

  useEffect(() => () => {
    if (messageTimerRef.current) {
      clearTimeout(messageTimerRef.current);
    }
  }, []);

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

  // Form Handlers
  async function handleAddDonor(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await request('/donors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: donorForm.name,
          age: parseInt(donorForm.age, 10),
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
        fetchHospitals();
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
    try {
      const data = await request('/allocations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: parseInt(allocationForm.request_id, 10),
          unit_id: parseInt(allocationForm.unit_id, 10)
        })
      });
      if (data.success) {
        showMessage('Blood allocated successfully!', 'success');
        setAllocationForm({ request_id: '', unit_id: '' });
        fetchAllocations();
        fetchRequests();
        fetchBloodUnits();
        fetchInventory();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error allocating blood', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error allocating blood');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateRequestStatus(requestId, status) {
    setLoading(true);
    try {
      const data = await request(`/requests/${requestId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      if (data.success) {
        showMessage('Request status updated!', 'success');
        fetchRequests();
        fetchStatistics();
      } else {
        showMessage(data.detail || 'Error updating status', 'error');
      }
    } catch (e) {
      handleApiError(e, 'Error updating request status');
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

  function DonorsView() {
    return (
      <div className="donors-container">
        <h2 className="section-title">Manage Donors</h2>

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
                onChange={e => setDonorForm(prev => ({...prev, age: e.target.value}))}
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
                placeholder="Contact Number *"
                value={donorForm.contact}
                onChange={e => setDonorForm(prev => ({...prev, contact: e.target.value}))}
                required
              />
              <input
                autoComplete="off"
                type="email"
                placeholder="Email"
                value={donorForm.email}
                onChange={e => setDonorForm(prev => ({...prev, email: e.target.value}))}
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
                  </tr>
                </thead>
                <tbody>
                  {donors.map(donor => (
                    <tr key={donor.DonorID}>
                      <td>{donor.DonorID}</td>
                      <td>{donor.DonorName}</td>
                      <td>{donor.Age}</td>
                      <td><strong>{donor.BloodGroup}</strong></td>
                      <td>{donor.ContactNo}</td>
                      <td>{donor.TotalDonations}</td>
                      <td>{donor.LastDonationDate || 'Never'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No donors found</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  function PatientsView() {
    return (
      <div className="patients-container">
        <h2 className="section-title">Manage Patients</h2>

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
                placeholder="Contact Number *"
                value={patientForm.contact}
                onChange={e => setPatientForm(prev => ({...prev, contact: e.target.value}))}
                required
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
                  </tr>
                </thead>
                <tbody>
                  {patients.map(patient => (
                    <tr key={patient.PatientID}>
                      <td>{patient.PatientID}</td>
                      <td>{patient.PatientName}</td>
                      <td>{patient.Age}</td>
                      <td><strong>{patient.BloodGroupRequired}</strong></td>
                      <td>{patient.HospitalName}</td>
                      <td>{patient.ContactNo}</td>
                      <td>{patient.MedicalCondition || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No patients found</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  function RequestsView() {
    return (
      <div className="requests-container">
        <h2 className="section-title">Blood Requests</h2>

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
                    <th>Hospital</th>
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
                      <td>{req.HospitalName}</td>
                      <td>
                        <span className={`status-badge ${req.Status?.toLowerCase()}`}>
                          {req.Status}
                        </span>
                      </td>
                      <td>{new Date(req.RequestDate).toLocaleDateString()}</td>
                      <td>
                        {req.Status === 'Pending' && (
                          <>
                            <button 
                              onClick={() => handleUpdateRequestStatus(req.RequestID, 'Fulfilled')}
                              className="button"
                              disabled={loading}
                              style={{ marginRight: '5px', padding: '5px 10px', fontSize: '0.9rem' }}
                            >
                              <CheckCircle size={16} style={{ marginRight: '4px' }} /> Fulfill
                            </button>
                            <button 
                              onClick={() => handleUpdateRequestStatus(req.RequestID, 'Denied')}
                              className="button"
                              disabled={loading}
                              style={{ padding: '5px 10px', fontSize: '0.9rem', background: '#ef4444' }}
                            >
                              <XCircle size={16} style={{ marginRight: '4px' }} /> Deny
                            </button>
                          </>
                        )}
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
      </div>
    );
  }

  function ManagementView() {
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
                onChange={e => setAllocationForm(prev => ({...prev, request_id: e.target.value}))}
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
              >
                <option value="">Select Blood Unit *</option>
                {bloodUnits.filter(u => u.Status === 'Available').map(u => 
                  <option key={u.UnitID} value={u.UnitID}>
                    Unit {u.UnitID} - {u.BloodGroup} ({u.Component})
                  </option>
                )}
              </select>
            </div>
            <button type="submit" className="button" disabled={loading} style={{ marginTop: '15px' }}>
              {loading ? 'Allocating...' : 'Allocate Blood'}
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
          <h3 className="section-title" style={{ marginTop: 0 }}>Recent Allocations</h3>
          <div className="table-container">
            {allocations.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Allocation</th>
                    <th>Patient</th>
                    <th>Blood Group</th>
                    <th>Blood Bank</th>
                    <th>Component</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {allocations.slice(0, 10).map(allocation => (
                    <tr key={allocation.AllocationID}>
                      <td>{allocation.AllocationID}</td>
                      <td>{allocation.PatientName}</td>
                      <td><strong>{allocation.BloodGroup}</strong></td>
                      <td>{allocation.BloodBankName}</td>
                      <td>{allocation.Component}</td>
                      <td>{new Date(allocation.AllocationDate).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#6b7280' }}>No allocations recorded yet</p>
            )}
          </div>
        </div>
      </div>
    );
  }

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

      <header className="header">
        <div className="header-inner">
          <Heart className="header-icon" fill="white" />
          <span className="title">Blood Bank Management System</span>
        </div>
        <div style={{ fontSize: '14px', opacity: 0.75 }}>Saving lives, one donation at a time</div>
      </header>

      <div className="tabs">
        {[
          { id: 'dashboard', label: 'Dashboard' },
          { id: 'donors', label: 'Donors' },
          { id: 'patients', label: 'Patients' },
          { id: 'requests', label: 'Requests' },
          { id: 'management', label: 'Management' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab-button${activeTab !== tab.id ? ' inactive' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="container">
        {activeTab === 'dashboard' && <DashboardView />}
        {activeTab === 'donors' && <DonorsView />}
        {activeTab === 'patients' && <PatientsView />}
        {activeTab === 'requests' && <RequestsView />}
        {activeTab === 'management' && <ManagementView />}
      </div>
    </div>
  );
};

export default BloodBankManagement;

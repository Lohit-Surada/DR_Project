import { useEffect, useState } from 'react';
import {
  Calendar,
  Camera,
  Droplets,
  HeartPulse,
  LogOut,
  Mail,
  MapPin,
  Phone,
  Save,
  UserRound,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const calculateAge = (dobString) => {
  if (!dobString) return '';
  const birthDate = new Date(dobString);
  if (isNaN(birthDate.getTime())) return '';
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const m = today.getMonth() - birthDate.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age >= 0 ? String(age) : '';
};

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const SEX_OPTIONS = ['Male', 'Female', 'Other', 'Prefer not to say'];

export default function Profile() {
  const navigate = useNavigate();
  const { currentUser, logout, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [form, setForm] = useState({
    fullName: '',
    age: '',
    sex: '',
    dob: '',
    email: '',
    contactNo: '',
    address: '',
    bloodGroup: '',
  });

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (currentUser && !isEditing) {
      const dobVal = currentUser.dob || currentUser.dateOfBirth || '';
      const derivedAge = currentUser.age !== undefined && currentUser.age !== '' ? String(currentUser.age) : calculateAge(dobVal);
      setForm({
        fullName: currentUser.fullName || '',
        age: derivedAge,
        sex: currentUser.sex || '',
        dob: dobVal,
        email: currentUser.email || '',
        contactNo: currentUser.contactNo || currentUser.phone || '',
        address: currentUser.address || '',
        bloodGroup: currentUser.bloodGroup || '',
      });
    }
  }, [currentUser, isEditing]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => {
      const updated = { ...current, [name]: value };
      if (name === 'dob' && value && !current.age) {
        updated.age = calculateAge(value);
      }
      return updated;
    });
    setSaveSuccess(false);
    setError('');
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError('');
    try {
      const updatedUser = {
        ...currentUser,
        fullName: form.fullName.trim(),
        age: form.age ? String(form.age).trim() : '',
        sex: form.sex,
        dob: form.dob,
        dateOfBirth: form.dob,
        email: form.email.trim(),
        contactNo: form.contactNo.trim(),
        phone: form.contactNo.trim(),
        address: form.address.trim(),
        bloodGroup: form.bloodGroup,
      };

      await updateUser(updatedUser);
      setIsEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
    } catch (err) {
      setError(err.message || 'Failed to update profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setError('');
    if (currentUser) {
      const dobVal = currentUser.dob || currentUser.dateOfBirth || '';
      const derivedAge = currentUser.age !== undefined && currentUser.age !== '' ? String(currentUser.age) : calculateAge(dobVal);
      setForm({
        fullName: currentUser.fullName || '',
        age: derivedAge,
        sex: currentUser.sex || '',
        dob: dobVal,
        email: currentUser.email || '',
        contactNo: currentUser.contactNo || currentUser.phone || '',
        address: currentUser.address || '',
        bloodGroup: currentUser.bloodGroup || '',
      });
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  if (!currentUser) {
    return null;
  }

  const profileSummaryItems = [
    { label: 'Full Name', value: form.fullName || currentUser.fullName, icon: UserRound },
    { label: 'Age', value: form.age ? `${form.age} years` : '', icon: HeartPulse },
    { label: 'Sex', value: form.sex, icon: UserRound },
    { label: 'Date of Birth (DOB)', value: form.dob, icon: Calendar },
    { label: 'Email', value: form.email || currentUser.email, icon: Mail },
    { label: 'Contact No.', value: form.contactNo, icon: Phone },
    { label: 'Blood Group', value: form.bloodGroup, icon: Droplets },
    { label: 'Address', value: form.address, icon: MapPin, fullWidth: true },
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="medical-card overflow-hidden">
        {/* Profile Header Banner */}
        <div className="bg-gradient-to-r from-sky-700 via-sky-800 to-cyan-700 px-6 py-8 text-white sm:px-8">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-20 w-20 items-center justify-center rounded-full border-4 border-white/20 bg-white/10 text-2xl font-bold shadow-lg">
                {(form.fullName || currentUser.fullName || 'U').charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-sky-200">Patient & Research Profile</p>
                  {form.bloodGroup && (
                    <span className="rounded-full bg-rose-500/80 px-2.5 py-0.5 text-xs font-semibold text-white">
                      {form.bloodGroup}
                    </span>
                  )}
                  {form.sex && (
                    <span className="rounded-full bg-sky-900/60 px-2.5 py-0.5 text-xs font-medium text-sky-100">
                      {form.sex}
                    </span>
                  )}
                  {form.age && (
                    <span className="rounded-full bg-sky-900/60 px-2.5 py-0.5 text-xs font-medium text-sky-100">
                      {form.age} yrs
                    </span>
                  )}
                </div>
                <h1 className="mt-1 text-3xl font-bold">{form.fullName || currentUser.fullName || 'User Profile'}</h1>
                <p className="mt-1 text-sm text-sky-100/80">{form.email || currentUser.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {!isEditing ? (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="inline-flex items-center gap-2 rounded-xl border border-white/25 bg-white/15 px-4 py-2.5 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/25"
                >
                  <Camera className="h-4 w-4" aria-hidden="true" />
                  Edit Profile
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={isSaving}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-white/25 bg-white/10 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-white/20"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={isSaving}
                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-emerald-600 disabled:opacity-75"
                  >
                    <Save className="h-4 w-4" aria-hidden="true" />
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="border-b border-rose-200 bg-rose-50 px-6 py-3 text-sm font-medium text-rose-800">
            {error}
          </div>
        )}

        {saveSuccess && (
          <div className="border-b border-emerald-200 bg-emerald-50 px-6 py-3 text-sm font-medium text-emerald-800">
            Profile updated successfully. These details will automatically be included in your generated medical reports.
          </div>
        )}

        {/* Profile Content Body */}
        <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="section-label">Medical & Personal Details</p>
                  <p className="mt-1 text-xs text-slate-500">
                    These profile fields are used to expand your AI analysis medical reports.
                  </p>
                </div>
                <span className="text-xs font-medium text-sky-700">
                  {isEditing ? 'Editing Mode' : 'View Mode'}
                </span>
              </div>

              {isEditing ? (
                /* Edit Form */
                <div className="mt-6 space-y-4">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-slate-700">Full Name</label>
                    <input
                      name="fullName"
                      type="text"
                      placeholder="e.g. John Doe"
                      value={form.fullName}
                      onChange={handleChange}
                      className="input-field"
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-700">Date of Birth (DOB)</label>
                      <input
                        name="dob"
                        type="date"
                        value={form.dob}
                        onChange={handleChange}
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-700">Age</label>
                      <input
                        name="age"
                        type="number"
                        min="0"
                        max="130"
                        placeholder="e.g. 45"
                        value={form.age}
                        onChange={handleChange}
                        className="input-field"
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-700">Sex</label>
                      <select
                        name="sex"
                        value={form.sex}
                        onChange={handleChange}
                        className="input-field"
                      >
                        <option value="">Select Sex</option>
                        {SEX_OPTIONS.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-700">Blood Group</label>
                      <select
                        name="bloodGroup"
                        value={form.bloodGroup}
                        onChange={handleChange}
                        className="input-field"
                      >
                        <option value="">Select Blood Group</option>
                        {BLOOD_GROUPS.map((bg) => (
                          <option key={bg} value={bg}>
                            {bg}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-700">Email</label>
                      <input
                        name="email"
                        type="email"
                        placeholder="user@example.com"
                        value={form.email}
                        onChange={handleChange}
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-700">Contact No.</label>
                      <input
                        name="contactNo"
                        type="tel"
                        placeholder="+1 (555) 000-0000"
                        value={form.contactNo}
                        onChange={handleChange}
                        className="input-field"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-slate-700">Address</label>
                    <textarea
                      name="address"
                      rows={2}
                      placeholder="Street, City, State, ZIP code"
                      value={form.address}
                      onChange={handleChange}
                      className="input-field"
                    />
                  </div>
                </div>
              ) : (
                /* Display View — Key-Value Pairs without Table */
                <div className="mt-6 divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white px-5 py-2 shadow-sm">
                  {profileSummaryItems.map(({ label, value, icon: Icon }) => (
                    <div
                      key={label}
                      className="flex flex-col py-3 text-sm sm:flex-row sm:items-center sm:justify-between"
                    >
                      <span className="flex items-center gap-2 font-medium text-slate-600">
                        <Icon className="h-4 w-4 text-sky-600" aria-hidden="true" />
                        <span>{label}:</span>
                      </span>
                      <span className="mt-1 font-semibold text-slate-900 sm:mt-0 sm:text-right">
                        {value && String(value).trim() ? (
                          String(value).trim()
                        ) : (
                          <span className="font-normal italic text-slate-400">Not provided</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Account Details & Report Preview Box */}
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <p className="section-label">Medical Report Integration</p>
              <div className="mt-4 space-y-3 text-xs leading-5 text-slate-600">
                <p>
                  Any information provided here is directly embedded in your generated <b>Diabetic Retinopathy AI Analysis Report</b>.
                </p>
                <div className="rounded-xl border border-sky-200 bg-sky-50/80 p-3 text-slate-700">
                  <p className="font-semibold text-sky-900">Included in PDF Report:</p>
                  <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[11px] text-slate-600">
                    <li><b>Report Date:</b> Automatically recorded with timestamp</li>
                    <li><b>Full Name:</b> Used as patient / research subject identity</li>
                    <li><b>Demographics:</b> Age, Sex, Date of Birth (DOB)</li>
                    <li><b>Contact:</b> Email, Contact No., and Address</li>
                    <li><b>Clinical:</b> Blood Group for clinical context</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
              <p className="section-label">Account Information</p>
              <div className="mt-4 space-y-3 text-sm text-slate-700">
                <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200">
                  <span className="font-medium text-xs text-slate-500">Account Status</span>
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                    Active
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200">
                  <span className="font-medium text-xs text-slate-500">Role</span>
                  <span className="text-xs font-medium text-slate-800">Research User</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white px-3 py-2.5 ring-1 ring-slate-200">
                  <span className="font-medium text-xs text-slate-500">Member Since</span>
                  <span className="text-xs font-medium text-slate-800">
                    {new Date(currentUser.createdAt || Date.now()).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              {!isEditing ? (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="inline-flex flex-1 items-center justify-center rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-500"
                >
                  Edit Profile
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={isSaving}
                    className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-500 disabled:opacity-75"
                  >
                    <Save className="h-4 w-4" aria-hidden="true" />
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={isSaving}
                    className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

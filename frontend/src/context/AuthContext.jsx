import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
} from 'firebase/auth';
import { doc, getDoc, serverTimestamp, setDoc } from 'firebase/firestore';
import { auth, firestore } from '../services/firebase';

const AuthContext = createContext(null);

const getAuthErrorMessage = (error) => {
  const messages = {
    'auth/email-already-in-use': 'An account with this email already exists.',
    'auth/invalid-credential': 'Invalid email or password.',
    'auth/invalid-email': 'Please enter a valid email address.',
    'auth/weak-password': 'Password must be at least 6 characters long.',
  };

  return messages[error.code] || error.message || 'Authentication failed. Please try again.';
};

const localProfileKey = (userId) => `retinaiq-profile:${String(userId)}`;

function readLocalProfile(userId) {
  if (!userId) return {};
  try {
    return JSON.parse(window.localStorage.getItem(localProfileKey(userId)) || '{}');
  } catch {
    return {};
  }
}

function writeLocalProfile(userId, profile) {
  if (!userId) return;
  try {
    const existing = readLocalProfile(userId);
    window.localStorage.setItem(localProfileKey(userId), JSON.stringify({ ...existing, ...profile }));
  } catch {
    // Local storage error handling
  }
}

const profileFromFirebaseUser = (firebaseUser, profile = {}) => {
  const local = firebaseUser ? readLocalProfile(firebaseUser.uid) : {};
  const merged = { ...local, ...profile };
  return {
    id: firebaseUser ? firebaseUser.uid : '',
    fullName: merged.fullName || firebaseUser?.displayName || '',
    email: firebaseUser?.email || merged.email || '',
    dateOfBirth: merged.dateOfBirth || merged.dob || '',
    dob: merged.dob || merged.dateOfBirth || '',
    phone: merged.phone || merged.contactNo || firebaseUser?.phoneNumber || '',
    contactNo: merged.contactNo || merged.phone || firebaseUser?.phoneNumber || '',
    age: merged.age !== undefined && merged.age !== null ? String(merged.age) : '',
    sex: merged.sex || merged.gender || '',
    address: merged.address || '',
    bloodGroup: merged.bloodGroup || '',
    createdAt: merged.createdAt || firebaseUser?.metadata?.creationTime || new Date().toISOString(),
  };
};

async function getUserProfile(firebaseUser) {
  const localProfile = readLocalProfile(firebaseUser.uid);
  try {
    const snapshot = await getDoc(doc(firestore, 'users', firebaseUser.uid));
    const remoteData = snapshot.exists() ? snapshot.data() : {};
    const merged = { ...localProfile, ...remoteData };
    writeLocalProfile(firebaseUser.uid, merged);
    return profileFromFirebaseUser(firebaseUser, merged);
  } catch (error) {
    return profileFromFirebaseUser(firebaseUser, localProfile);
  }
}

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  useEffect(() => {
    return onAuthStateChanged(auth, async (firebaseUser) => {
      try {
        setCurrentUser(firebaseUser ? await getUserProfile(firebaseUser) : null);
      } catch {
        setCurrentUser(firebaseUser ? profileFromFirebaseUser(firebaseUser) : null);
      } finally {
        setIsAuthLoading(false);
      }
    });
  }, []);

  const login = useCallback(async (credentials) => {
    try {
      const result = await signInWithEmailAndPassword(auth, credentials.email.trim(), credentials.password);
      const user = await getUserProfile(result.user);
      setCurrentUser(user);
      return user;
    } catch (error) {
      throw new Error(getAuthErrorMessage(error));
    }
  }, []);

  const register = useCallback(async (payload) => {
    try {
      const result = await createUserWithEmailAndPassword(auth, payload.email.trim(), payload.password);
      if (payload.fullName?.trim()) {
        await updateProfile(result.user, { displayName: payload.fullName.trim() }).catch(() => {});
      }
      const initialProfile = {
        fullName: payload.fullName.trim(),
        email: result.user.email,
        dateOfBirth: payload.dateOfBirth || '',
        phone: payload.phone || '',
      };
      writeLocalProfile(result.user.uid, initialProfile);
      await setDoc(doc(firestore, 'users', result.user.uid), {
        ...initialProfile,
        createdAt: serverTimestamp(),
      }).catch((err) => {
        console.warn('Firestore user doc init note:', err.message);
      });
      await signOut(auth);
      return profileFromFirebaseUser(result.user, initialProfile);
    } catch (error) {
      throw new Error(getAuthErrorMessage(error));
    }
  }, []);

  const logout = useCallback(async () => {
    await signOut(auth);
    setCurrentUser(null);
  }, []);

  const updateUser = useCallback(async (updatedUser) => {
    const firebaseUser = auth.currentUser;
    const userId = firebaseUser?.uid || updatedUser?.id || currentUser?.id || 'anonymous';

    const payload = {
      fullName: updatedUser.fullName !== undefined ? updatedUser.fullName : (currentUser?.fullName || ''),
      email: firebaseUser?.email || updatedUser.email || currentUser?.email || '',
      dateOfBirth: updatedUser.dateOfBirth || updatedUser.dob || currentUser?.dateOfBirth || '',
      dob: updatedUser.dob || updatedUser.dateOfBirth || currentUser?.dob || '',
      phone: updatedUser.phone || updatedUser.contactNo || currentUser?.phone || '',
      contactNo: updatedUser.contactNo || updatedUser.phone || currentUser?.contactNo || '',
      age: updatedUser.age !== undefined && updatedUser.age !== null ? String(updatedUser.age) : (currentUser?.age || ''),
      sex: updatedUser.sex !== undefined ? updatedUser.sex : (currentUser?.sex || ''),
      address: updatedUser.address !== undefined ? updatedUser.address : (currentUser?.address || ''),
      bloodGroup: updatedUser.bloodGroup !== undefined ? updatedUser.bloodGroup : (currentUser?.bloodGroup || ''),
    };

    // 1. Immediately persist to localStorage
    writeLocalProfile(userId, payload);

    // 2. Immediately update state
    const mergedUser = {
      ...currentUser,
      ...updatedUser,
      ...payload,
      id: userId,
      email: firebaseUser?.email || updatedUser.email || currentUser?.email || '',
    };
    setCurrentUser(mergedUser);

    // 3. Sync to Firebase in background without throwing errors if rules block it
    if (firebaseUser) {
      try {
        if (payload.fullName) {
          updateProfile(firebaseUser, { displayName: payload.fullName }).catch(() => {});
        }
        setDoc(doc(firestore, 'users', firebaseUser.uid), payload, { merge: true }).catch((err) => {
          console.warn('Remote Firestore sync note (local profile preserved):', err.message);
        });
      } catch (err) {
        console.warn('Profile background sync note:', err);
      }
    }

    return mergedUser;
  }, [currentUser]);

  const value = useMemo(
    () => ({
      currentUser,
      isAuthenticated: Boolean(currentUser),
      isAuthLoading,
      login,
      register,
      logout,
      updateUser,
    }),
    [currentUser, isAuthLoading, login, register, logout, updateUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider');
  }

  return context;
}

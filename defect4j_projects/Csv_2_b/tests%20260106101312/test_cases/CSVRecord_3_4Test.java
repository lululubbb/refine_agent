package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_3_4Test {

    private Map<String, Integer> mapping;
    private String[] values;
    private CSVRecord recordWithMapping;
    private CSVRecord recordWithoutMapping;

    @BeforeEach
    void setUp() {
        values = new String[] { "val0", "val1", "val2" };
        mapping = new HashMap<>();
        mapping.put("header0", 0);
        mapping.put("header1", 1);
        mapping.put("header2", 2);

        recordWithMapping = new CSVRecord(values, mapping, null, 1L);
        recordWithoutMapping = new CSVRecord(values, null, null, 2L);
    }

    @Test
    @Timeout(8000)
    void testGet_WithValidName_ReturnsValue() {
        assertEquals("val0", recordWithMapping.get("header0"));
        assertEquals("val1", recordWithMapping.get("header1"));
        assertEquals("val2", recordWithMapping.get("header2"));
    }

    @Test
    @Timeout(8000)
    void testGet_WithInvalidName_ReturnsNull() {
        assertNull(recordWithMapping.get("nonexistent"));
    }

    @Test
    @Timeout(8000)
    void testGet_WithNullName_ReturnsNull() {
        assertNull(recordWithMapping.get(null));
    }

    @Test
    @Timeout(8000)
    void testGet_WithoutMapping_ThrowsIllegalStateException() {
        IllegalStateException ex = assertThrows(IllegalStateException.class, () -> recordWithoutMapping.get("header0"));
        assertEquals("No header mapping was specified, the record values can't be accessed by name", ex.getMessage());
    }

    @Test
    @Timeout(8000)
    void testPrivateGetMethodUsingReflection() throws Exception {
        Method getMethod = CSVRecord.class.getDeclaredMethod("get", String.class);
        getMethod.setAccessible(true);

        // valid name
        Object val = getMethod.invoke(recordWithMapping, "header1");
        assertEquals("val1", val);

        // invalid name returns null
        val = getMethod.invoke(recordWithMapping, "nonexistent");
        assertNull(val);

        // null name returns null
        val = getMethod.invoke(recordWithMapping, (Object) null);
        assertNull(val);

        // without mapping throws IllegalStateException wrapped in InvocationTargetException
        CSVRecord noMapping = new CSVRecord(values, null, null, 3L);
        try {
            getMethod.invoke(noMapping, "header0");
            fail("Expected IllegalStateException");
        } catch (java.lang.reflect.InvocationTargetException e) {
            Throwable cause = e.getCause();
            assertTrue(cause instanceof IllegalStateException);
            assertEquals("No header mapping was specified, the record values can't be accessed by name", cause.getMessage());
        }
    }
}
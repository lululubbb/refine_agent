package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_3_1Test {

    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        values = new String[] { "value1", "value2" };
    }

    @Test
    @Timeout(8000)
    public void testGet_WithValidName_ReturnsValue() {
        CSVRecord record = new CSVRecord(values, mapping, null, 1L);
        String result = record.get("header1");
        assertEquals("value1", result);

        result = record.get("header2");
        assertEquals("value2", result);
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNameNotInMapping_ReturnsNull() {
        CSVRecord record = new CSVRecord(values, mapping, null, 1L);
        String result = record.get("header3");
        assertNull(result);
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNullMapping_ThrowsIllegalStateException() {
        CSVRecord record = new CSVRecord(values, null, null, 1L);
        IllegalStateException exception = assertThrows(IllegalStateException.class, () -> {
            record.get("header1");
        });
        assertEquals("No header mapping was specified, the record values can't be accessed by name", exception.getMessage());
    }

    @Test
    @Timeout(8000)
    public void testGet_PublicMethodInvocation_WithReflection() throws Exception {
        CSVRecord record = new CSVRecord(values, mapping, null, 1L);
        Method getMethod = CSVRecord.class.getDeclaredMethod("get", String.class);
        getMethod.setAccessible(true);

        Object result = getMethod.invoke(record, "header1");
        assertEquals("value1", result);

        result = getMethod.invoke(record, "header3");
        assertNull(result);

        CSVRecord recordNullMapping = new CSVRecord(values, null, null, 1L);
        try {
            getMethod.invoke(recordNullMapping, "header1");
            fail("Expected an exception to be thrown");
        } catch (java.lang.reflect.InvocationTargetException e) {
            Throwable cause = e.getCause();
            assertTrue(cause instanceof IllegalStateException);
            assertEquals("No header mapping was specified, the record values can't be accessed by name", cause.getMessage());
        }
    }
}
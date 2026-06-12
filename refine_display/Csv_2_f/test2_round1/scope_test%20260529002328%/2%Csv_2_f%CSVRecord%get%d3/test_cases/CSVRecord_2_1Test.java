package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_2_1Test {
    private CSVRecord csvRecord;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("first", 0);
        mapping.put("second", 1);
        mapping.put("third", 2);
        csvRecord = new CSVRecord(values, mapping, "This is a comment", 1);
    }

    @Test
    public void testget_validIndex() throws Exception {
        String result = invokeGetMethod(1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testget_firstIndex() throws Exception {
        String result = invokeGetMethod(0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testget_lastIndex() throws Exception {
        String result = invokeGetMethod(2);
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testget_outOfBoundsLow() throws Exception {
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> invokeGetMethod(-1));
    }

    @Test
    public void testget_outOfBoundsHigh() throws Exception {
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> invokeGetMethod(3));
    }

    private String invokeGetMethod(int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        try {
            return (String) method.invoke(csvRecord, index);
        } catch (InvocationTargetException e) {
            throw e.getCause(); // Rethrow the underlying cause
        }
    }
}
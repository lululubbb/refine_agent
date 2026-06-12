package org.apache.commons.csv;

import java.io.Serializable;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_2Test {
    private CSVRecord csvRecord;

    @BeforeEach
    public void setUp() {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        csvRecord = new CSVRecord(values, mapping, null, 1);
    }

    @Test
    public void testGet_validIndex() throws Exception {
        String result = invokeGetMethod(1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_firstIndex() throws Exception {
        String result = invokeGetMethod(0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_lastIndex() throws Exception {
        String result = invokeGetMethod(2);
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_invalidIndex() throws Exception {
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            try {
                invokeGetMethod(3);
            } catch (InvocationTargetException e) {
                throw (Throwable) e.getCause();
            }
        });
    }

    @Test
    public void testGet_negativeIndex() throws Exception {
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            try {
                invokeGetMethod(-1);
            } catch (InvocationTargetException e) {
                throw (Throwable) e.getCause();
            }
        });
    }

    @Test
    public void testGet_emptyString() throws Exception {
        String[] values = {""};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        CSVRecord emptyRecord = new CSVRecord(values, mapping, null, 1);
        String result = invokeGetMethod(emptyRecord, 0);
        Assertions.assertEquals("", result);
    }

    private String invokeGetMethod(int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        return (String) method.invoke(csvRecord, index);
    }

    private String invokeGetMethod(CSVRecord record, int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        return (String) method.invoke(record, index);
    }
}
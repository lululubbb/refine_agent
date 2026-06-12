package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_1Test {

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGetMethod(record, 1);
        
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_zeroIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGetMethod(record, 0);
        
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_lastIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGetMethod(record, 2);
        
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_outOfBounds() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGetMethod(record, 3);
        });
    }

    @Test
    public void testGet_negativeIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGetMethod(record, -1);
        });
    }

    @Test
    public void testGet_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGetMethod(record, 0);
        });
    }

    @Test
    public void testGet_nullValue() throws Exception {
        String[] values = {null, "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = invokeGetMethod(record, 0);
        
        Assertions.assertNull(result);
    }

    private String invokeGetMethod(CSVRecord record, int index) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("get", int.class);
        method.setAccessible(true);
        try {
            return (String) method.invoke(record, index);
        } catch (InvocationTargetException e) {
            throw e.getCause(); // Rethrow the underlying cause
        }
    }
}
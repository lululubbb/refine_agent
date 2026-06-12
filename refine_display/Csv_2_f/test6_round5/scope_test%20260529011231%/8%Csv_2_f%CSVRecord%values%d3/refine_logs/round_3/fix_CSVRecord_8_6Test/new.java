package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_6Test {

    @Test
    public void testvalues_normalCase() throws Exception {
        String[] inputValues = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] inputValues = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_withNullValues() throws Exception {
        String[] inputValues = {null, "value2", null};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_singleElement() throws Exception {
        String[] inputValues = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_consistentWithMapping() throws Exception {
        String[] inputValues = {"value1", "value2"};
        Map<String, Integer> mapping = Collections.singletonMap("value1", 0);
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_withDifferentSizes() throws Exception {
        String[] inputValues = {"value1", "value2", "value3", "value4", "value5"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }

    @Test
    public void testvalues_withEmptyAndNull() throws Exception {
        String[] inputValues = {null, "", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(inputValues, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        String[] result = (String[]) method.invoke(record);
        
        Assertions.assertArrayEquals(inputValues, result);
    }
}
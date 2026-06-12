package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_12_3Test {

    @Test
    public void testtoString_emptyArray() throws Exception {
        String[] values = new String[0];
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testtoString_singleValue() throws Exception {
        String[] values = {"value1"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testtoString_multipleValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_withNullValues() throws Exception {
        String[] values = {"value1", null, "value3"};
        CSVRecord record = new CSVRecord(values, Collections.emptyMap(), null, 0);
        String result = invokeToString(record);
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    private String invokeToString(CSVRecord record) throws Exception {
        Method method = CSVRecord.class.getDeclaredMethod("toString");
        method.setAccessible(true);
        return (String) method.invoke(record);
    }
}